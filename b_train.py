import fire, wandb, os, json, pdb, torch
from sinabs.from_torch import from_model
from training.models import (
    convert_to_dynap,
    convert_sinabs_to_exodus,
    compute_output_dim,
)
from training.trainer import Trainer
from training.models import get_model_for_baseline, get_model_for_speck
from training.models.model import SynSenseEyeTracking
from training.models.baseline_3et import Baseline_3ET
from data import get_dataloader, get_indexes
from data.seet_dataset import get_seet_dataloader
from thop import profile


def launch_fire(
    # wandb/generic
    project_name="event_eye_tracking",
    arch_name="retina",
    dataset_name="ini-30",
    run_name=None,
    output_dir="/datasets/pbonazzi/retina/output/",
    data_dir="/datasets/pbonazzi/evs_eyetracking/d_inivation_eye",
    path_to_run=None,
    # dataset_params
    val_idx=1,
    synthetic_dataset=True,
    overfit=False,
    input_channel=2,
    img_width=64,
    img_height=64,
    num_bins=40,
    # dataset_params - accumulation/slicing
    events_per_frame=300,
    events_per_step=20,
    sliced_dataset=True,
    fixed_window=True,
    fixed_window_dt=2_500,  # us
    remove_experiments=True,
    # dataset_params - augmentation
    shuffle=True,
    spatial_factor=0.25,
    center_crop=True,
    uniform_noise=False,
    event_drop=False,
    time_jitter=False,
    pre_decimate=False,
    pre_decimate_factor=4,
    denoise_evs=False,
    # training_params
    device="cuda",
    lr_model=1e-3,
    lr_model_lpf=1e-4,
    lr_model_lpf_tau=1e-3,
    train_with_sinabs=False,
    train_with_exodus=False,
    train_ann_to_snn=False,
    train_with_mem=False,
    num_epochs=1,
    batch_size=16,
    # training_params - optimization
    optimizer="Adam",
    reset_states_sinabs=True,
    scheduler="StepLR",
    # training_params - LPF layer
    train_with_lpf=True,
    lpf_tau_mem_syn=(5.0, 5.0),  # (50, 50),
    lpf_kernel_size=30,  # 20
    lpf_init=0.01,
    lpf_train=True,
    # training_params - Decimation layer
    train_with_dec=True,
    decimation_rate=1,
    # training_params - IAF layer
    spike_multi=False,
    spike_reset=False,
    spike_surrogate=True,
    spike_window=0.5,
    # training_parms - euclidian loss
    euclidian_loss=False,
    w_euclidian_loss=7.5,
    # training_params - focal loss
    focal_loss=False,
    bbox_w=5,
    # training_params - yolo loss
    yolo_loss=True,
    num_classes=0,
    num_boxes=2,
    SxS_Grid=4,
    w_box_loss=7.5,  # 7.5,
    w_tracking_loss=0,
    w_conf_loss=1.5,  # 1.5,
    w_spike_loss=0,
    # training_params - speck loss
    w_synap_loss=0,  # 1e-8,
    synops_lim=(1e3, 1e6),
    w_input_loss=0,  # 1e-8,
    w_fire_loss=0,  # 1e-4,
    firing_lim=(0.3, 0.4),
):
    assert torch.cuda.is_available()
    torch.autograd.set_detect_anomaly(True)
    torch.multiprocessing.set_start_method("spawn", force=True)
    torch.set_default_tensor_type(torch.cuda.FloatTensor)
    #torch.set_num_threads(10)
    #torch.set_num_interop_threads(10)

    # Logging
    wandb.init(
        mode="disabled" if overfit else "run",
        name=run_name,
        project=project_name,
        dir=output_dir,
        config={
            "architecture": arch_name,
            "dataset": dataset_name,
            "epochs": num_epochs,
        },
    )

    # Output Folder
    run_name = wandb.run.name
    index = run_name.rindex("-")
    out_dir = os.path.join(
        output_dir, "wandb", f"{run_name[index+1:]}-{run_name[:index]}"
    )
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "video"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "spikes"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "models"), exist_ok=True)

    if not train_with_sinabs :
        yolo_loss = False
        euclidian_loss = True

    # Load/ Init
    if path_to_run != None:
        training_params = json.load(
            open(os.path.join(path_to_run, "training_params.json"), "r")
        )
        dataset_params = json.load(
            open(os.path.join(path_to_run, "dataset_params.json"), "r")
        )
        layers_config = json.load(
            open(os.path.join(path_to_run, "layer_configs.json"), "r")
        )
    else:
        training_params = {
            "device": device,
            "lr_model": lr_model,
            "lr_model_lpf": lr_model_lpf,
            "lr_model_lpf_tau": lr_model_lpf_tau,
            "decimation_rate": decimation_rate,
            "num_epochs": num_epochs,
            "batch_size": batch_size,
            "optimizer": optimizer,
            "scheduler": scheduler,
            "train_with_sinabs": train_with_sinabs,
            "train_with_exodus": train_with_exodus,
            "train_ann_to_snn": train_ann_to_snn,
            "train_with_lpf": train_with_lpf and train_with_sinabs,
            "lpf_tau_mem_syn": lpf_tau_mem_syn,
            "lpf_kernel_size": min(lpf_kernel_size, num_bins),
            "lpf_init": lpf_init,
            "lpf_train": lpf_train,
            "train_with_mem": train_with_mem and train_with_sinabs,
            "train_with_dec": train_with_dec,
            "reset_states_sinabs": reset_states_sinabs,
            "w_euclidian_loss": w_euclidian_loss,
            "w_box_loss": w_box_loss,
            "w_conf_loss": w_conf_loss,
            "w_spike_loss": w_spike_loss,
            "w_synap_loss": w_synap_loss,
            "w_tracking_loss": w_tracking_loss,
            "synops_lim": synops_lim,
            "w_input_loss": w_input_loss,
            "w_fire_loss": w_fire_loss,
            "firing_lim": firing_lim,
            "out_dir": out_dir,
            "euclidian_loss": euclidian_loss,
            "focal_loss": focal_loss,
            "yolo_loss": yolo_loss,
            "SxS_Grid": SxS_Grid,
            "num_classes": num_classes,
            "num_boxes": num_boxes,
            "bbox_w": bbox_w,
            "spike_multi": spike_multi,
            "spike_reset": spike_reset,
            "spike_surrogate": spike_surrogate,
            "spike_window": spike_window,
        }
        input_channel = 1 if synthetic_dataset else input_channel
        dataset_params = {
            "synthetic_dataset": synthetic_dataset,
            "data_dir": data_dir,
            "num_bins": num_bins,
            "events_per_frame": events_per_frame,
            "events_per_step": events_per_step,
            "input_channel": input_channel,
            "img_width": img_width,
            "img_height": img_height,
            "sliced_dataset": sliced_dataset,
            "fixed_window": fixed_window,
            "fixed_window_dt": fixed_window_dt,
            "remove_experiments": remove_experiments,
            "shuffle": shuffle,
            "spatial_factor": spatial_factor,
            "center_crop": center_crop,
            "uniform_noise": uniform_noise,
            "event_drop": event_drop,
            "time_jitter": time_jitter,
            "pre_decimate": pre_decimate,
            "pre_decimate_factor": pre_decimate_factor,
            "denoise_evs": denoise_evs,
        }

        # Model
        training_params["output_dim"] = compute_output_dim(training_params)
        if train_with_sinabs:
            if dataset_params["img_width"] <= 128 or dataset_params["img_height"] <= 128:
                layers_config = get_model_for_speck(dataset_params, training_params)
            else:
                layers_config = get_model_for_baseline(dataset_params, training_params)

        training_params["train_idxs"], training_params["val_idxs"] = get_indexes(
            val_idx=val_idx,
            remove_experiments=dataset_params["remove_experiments"],
            overfit=overfit,
        )

        json.dump(training_params, open(f"{out_dir}/training_params.json", "w"))
        json.dump(dataset_params, open(f"{out_dir}/dataset_params.json", "w"))
        if train_with_sinabs:
            json.dump(layers_config, open(f"{out_dir}/layer_configs.json", "w"))

    # Model
    if train_with_sinabs:
        model = SynSenseEyeTracking(dataset_params, training_params, layers_config)
        model = from_model(
            model.seq,
            add_spiking_output=False,
            synops=True,
            batch_size=training_params["batch_size"],
        )
    else:
        model = Baseline_3ET(
            height=dataset_params["img_height"],
            width=dataset_params["img_width"],
            input_dim=dataset_params["input_channel"],
            device=torch.device(device),
        )

    # Validate
    input_shape = (
        dataset_params["input_channel"],
        dataset_params["img_width"],
        dataset_params["img_height"],
    )
    if (
        dataset_params["img_width"] <= 128 or dataset_params["img_height"] <= 128
    ) and train_with_sinabs:
        dynapcnn_net = convert_to_dynap(
            model.spiking_model.cpu(), input_shape=input_shape
        )
        dynapcnn_net.make_config(device="speck2fmodule")

    # Datasets
    if not synthetic_dataset:
        train_loader = get_dataloader(
            name="train",
            device=torch.device(device),
            dataset_params=dataset_params,
            training_params=training_params,
            shuffle=True,
        )

        val_loader = get_dataloader(
            name="val",
            device=torch.device(device),
            dataset_params=dataset_params,
            training_params=training_params,
            shuffle=False,
        )
    else:
        train_loader, val_loader = get_seet_dataloader(dataset_params, training_params)

    # Accelerate
    model = model.to(torch.device(device))
    if train_with_exodus:
        model.spiking_model = convert_sinabs_to_exodus(model.spiking_model)
        print("Model converted to EXODUS")

    # Trainer
    if train_with_sinabs:
        model.spiking_model(
            torch.ones(
                training_params["batch_size"] * dataset_params["num_bins"], *input_shape
            ).to(torch.device(device))
        )
    trainer = Trainer(model, train_loader, val_loader)
    trainer.set_parameters(training_params, dataset_params)
    if path_to_run != None:
        trainer.load(path_to_run)
    trainer.set_loss(training_params, dataset_params)
    trainer.train()


if __name__ == "__main__":
    fire.Fire(launch_fire)
