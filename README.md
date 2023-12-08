# Event-Based Spiking Neuron Network for Eye Tracking on SynSense Neuromorphic Vision Chip Speck

#  👀 A Low-Power Neuromorphic Approach for Efficient Eye-Tracking   👀
[![PWC](https://img.shields.io/endpoint.svg?url=https://paperswithcode.com/badge/tinytracker-ultra-fast-and-ultra-low-power/gaze-estimation-on-gazecapture)](https://paperswithcode.com/paper/tinytracker-ultra-fast-and-ultra-low-power)
[![PWC](https://img.shields.io/endpoint.svg?url=https://paperswithcode.com/badge/a-low-power-neuromorphic-approach-for/pupil-tracking-on-ini-30)](https://paperswithcode.com/sota/pupil-tracking-on-ini-30?p=a-low-power-neuromorphic-approach-for)

### [💻 Blog](https://pietrobonazzi.com/projects/retina) |[📜 Paper](https://arxiv.org/pdf/2312.00425.pdf) | [🗂️ Data](https://pietrobonazzi.com/projects/retina)

[A Low-Power Neuromorphic Approach for Efcient Eye-Tracking](https://arxiv.org/abs/2307.07813)  
 [🧑🏻‍🚀 Pietro Bonazzi ](https://linkedin.com/in/pietrobonazzi)\*<sup>1</sup>,
 Sizhen Bian <sup>1</sup>,
 Giovanni Lippolis <sup>1</sup>,
 Yawei Li<sup>1</sup>,
 Sadique Sheik <sup>1</sup>,
 Michele Magno<sup>1</sup>  <br>

\*denotes equal contribution  
ETH Zurich, Switzerland  <br> 

## ✉️ Citation ❤️
```
@article{bonazzi2023retina,
  title={A Low-Power Neuromorphic Approach for Efcient Eye-Tracking},
  author={Pietro Bonazzi, Sizhen Bian, Giovanni Lippolis, Yawei Li, Sadique Sheik, Michele Magno},
  year={2023},
}
```
## 🚀 TL;DR quickstart 🚀

### Clone the repo

```
git clone https://gitlab.ethz.ch/pbonazzi/retina.git
cd retina
```


### Create the environment

First, make sure your cmake is up to date and install `dv_processing` dependencies ["https://gitlab.com/inivation/dv/dv-processing"]

Then, create the environment:

```
python3.10 -m venv venv
source venv/bin/activate

pip install pandas wandb fire matplotlib tqdm
pip install tonic sinabs sinabs-dynapcnn
pip install torch==2.0.0+cu117 torchvision==0.15.1+cu117 torchaudio==2.0.1 --index-url https://download.pytorch.org/whl/cu117
pip install git+https://gitlab.com/inivation/dv/dv-processing #https://dv-processing.inivation.com/rel_1.7/installation.html 
```


### Get the dataset
dependencies ["https://pietrobonazzi.com/projects/retina"]


Verify `EyeTrackingDataSet_FromInivation`

```
.
├── name
│   ├── annotations.csv
│   └── events.aedat4
├── ...
├── silver.csv
```


## Training
--args : See the list of arguments in the launch_fire function

```
python b_train.py --args
```

