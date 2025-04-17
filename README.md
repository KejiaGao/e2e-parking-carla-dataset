# E2E Parking Dataset: An Open Benchmark for End-to-End Autonomous Parking


This repository contains the code for the paper 
[E2E Parking Dataset: An Open Benchmark for End-to-End Autonomous Parking](https://arxiv.org/abs/2504.10812).

This work presents a high-quality dataset for the work [E2E Parking: Autonomous Parking by the End-to-end Neural Network on the CARLA Simulator](https://github.com/qintonguav/e2e-parking-carla). The Transformer model learns to map the sensor inputs into control signals. 
Training data generation and closed-loop evaluation is conducted on CARLA simulator 0.9.11. Utilizing the same original model architecture, the model trained on our dataset achieves an overall Target Success Rate (TSR) of 85.16%, which essentially reproduces the results reported by the original authors. With the further rule-based control, the TSR can increase to 97.66%.


## Setup

Clone the repo, setup CARLA 0.9.11, and build the conda environment:

```Shell
git clone https://github.com/KejiaGao/e2e-parking-carla-dataset.git
cd e2e-parking-carla-dataset/
conda env create -f environment.yml
conda activate E2EParking
chmod +x setup_carla.sh
./setup_carla.sh
```
CUDA 11.7 is used as default. The original authors also validate the compatibility of CUDA 10.2 and 11.3.

## Dataset acquisition and introduction
```
cd e2e-parking-carla-dataset/
```
Download the dataset in the current directory with this link: https://pan.baidu.com/s/1PoMSfgZQMnUGlhi7S5fFZw?pwd=2ik6
```
mkdir e2e_parking
unzip E2EParking_dataset_Gen5B.zip -d e2e_parking
```
Gen5B is a personal code name for Generation 5B, which is the latest dataset for this project. Since Gen 1, Gen 2, and Gen 3 had problems and were not recorded in the experimental results of the paper, Gen 4 and Gen 5 are referred to as Gen 1 and Gen 2 in the paper.

In Gen5B_train, there are 14 subfolders named with three numbers and two letters. The 3 numbers stand for the random seed assigned to task 0 (corresponding to the first target slot 2-2). For subsequent tasks, each time the task index increases by 1, the random seed value also increases by 1. There are 6 options for the two letters: FL (far-left), FR (far-right), ML (middle-left), MR (middle-right), NL (near-left) and NR (near-right), which means the initial position of each task in the bird's eye view. For example, 032FL means in this subfolder, the initial position of the vehicle in the 16 tasks (task 0 to 15 or parking slot 2-2 to 3-16) is far-left relative to the target slot in BEV; random seed for task 0 is 32, the seed value increases with the task index, until 47 is assigned to task 15. Subfolder task11_shadow_train and task12_shadow_train contain the routes with shadow on target slot 3-8 and 3-10, respectively. The 3 numbers are random seed assigned to corresponding target slot.

In Gen5B_val, 000VA1, 000VA2, 016VA1 and 016VA2 contain routes where initial positions are flexible, while the way to assign the random seed remains the same. Subfolder task11_shadow_val and task12_shadow_val serve as validation counterparts to the corresponding training sets.

The tree structure of dataset is listed as follows:
```
Gen5B_train                            | Gen5B_val
-------------------------------------  | -----------------------------
├── 000FL                              | ├── 000VA1
├── 000FR                              | ├── 000VA2
├── 000ML                              | ├── 016VA1
├── 000MR                              | ├── 016VA2
├── 000NL                              | ├── 032ML
├── 000NR                              | ├── 032MR
├── 016FL                              | ├── task11_shadow_val
├── 016FR                              | │   ├── 011FL
├── 016ML                              | │   ├── 011FR
├── 016MR                              | │   ├── 027ML
├── 016NL                              | │   └── 027MR
├── 016NR                              | └── task12_shadow_val
├── 032FL                              |     ├── 012FR
├── 032FR                              |     ├── 012ML
├── task11_shadow_train                |     ├── 028FL
│   ├── 011FL                          |     └── 028MR
│   ├── 011FR                          |
│   ├── 011ML                          |
│   ├── 011MR                          |
│   ├── 011NL                          |
│   ├── 011NR                          |
│   ├── 027FL                          |
│   ├── 027FR                          |
│   ├── 027ML                          |
│   ├── 027MR                          |
│   ├── 027NL                          |
│   └── 027NR                          |
├── task12_shadow_train                |
│   ├── 012FL                          |
│   ├── 012FR                          |
│   ├── 012ML                          |
│   ├── 012MR                          |
│   ├── 012NL                          |
│   ├── 012NR                          |
│   ├── 028FL                          |
│   ├── 028FR                          |
│   ├── 028ML                          |
│   ├── 028MR                          |
│   ├── 028NL                          |
│   └── 028NR                          |

```

## Evaluation (Inference with pre-trained model)
For inference, the original authors prepare a [pre-trained model](https://drive.google.com/file/d/1XOlzBAb9W91R6WOB-srgdY8AZH3fXlML/view?usp=sharing). This pre-trained model has an overall success rate of around 75%. We have tried to train models on our dataset based on this pre-trained model and the Target Success Rate drops so we recommend training the model without the pre-trained model.


The first step is to launch a CARLA server:

```Shell
./carla/CarlaUE4.sh -opengl
```

In a separate terminal, use the script below for trained model evaluation:
```Shell
python3 carla_parking_eva.py
```

The main variables to set for this script:
```
--model_path        -> path to model.ckpt
--eva_epochs        -> number of eva epochs (default: 4')
--eva_task_nums     -> number of evaluation task (default: 16')
--eva_parking_nums  -> number of parking nums for every slot (default: 6')
--eva_result_path   -> path to save evaluation result csv file
--shuffle_veh       -> shuffle static vehicles between tasks (default: True)
--shuffle_weather   -> shuffle weather between tasks (default: False)
--random_seed       -> random seed to initialize env (default: 0)
```
When the evaluation is completed, metrics will be saved to csv files located at '--eva_result_path'.

## Dataset and Training

### Training Data Generation
The original authors have provided the tools for manual parking data generation, which is the way I create the dataset. 
The first step is to launch a CARLA server:

```Shell
./carla/CarlaUE4.sh -opengl
```

In a separate terminal, use the script below for generating training data:
```Shell
python3 carla_data_gen.py
```

The main variables to set for this script:
```
--save_path         -> path to save sensor data (default: ./e2e_parking/)
--task_num          -> number of parking task (default: 16)
--shuffle_veh       -> shuffle static vehicles between tasks (default: True)
--shuffle_weather   -> shuffle weather between tasks (default: False)
--random_seed       -> random seed to initialize env; if sets to 0, use current timestamp as seed (default: 0)
```

Keyboard Control designed by original authors (not recommended):
```
w/a/s/d:    throttle/left_steer/right_steer/hand_brake
space:      brake
q:          reverse gear
BackSpace:  reset the current task
TAB:        switch camera view
```

Functional mapping of XBOX controller (recommended):
```
LS, Left Stick:     steering
RT, Right Trigger:  throttle
LT, Left Trigger:   brake
LB, Left Bumper:    handbrake
Button A:           switch first / reverse gear:
Button Y:           reset the current task
RB, Right Bumper:   switch camera view
```

Conditions for successful parking:
```
position: vehicle center to slot center < 0.5 meter
orientation: rotation error < 0.5 degree
duration: satisfy the above two conditions for 60 frames
```
The target parking slot is marked with a red 'T'. 

The program automatically switches to the next task when the current one is completed.

Any collision will reset the task.

### Training script

The code for training is provided in [pl_train.py](./pl_train.py) \
Run the script in the terminal to start training:
```Shell
python pl_train.py 
```
To configure the training parameters, please refer to [training.yaml](./config/training.yaml), including training data path, number of epochs and checkpoint path.

To select the GPU(s) for training, modify the setting in [pl_train.py](./pl_train.py). The parameter ```num_gpus``` can be automatically detected and doesn't need changing anymore.

For instance, 4 GPU parallel training:
```
line 2: os.environ['CUDA_VISIBLE_DEVICES'] = '4,5,6,7'
```



## Bibtex
If this work is helpful for your research, please consider citing our paper with the following BibTeX information.

```
@misc{gao2025e2eparkingdatasetopen,
      title={E2E Parking Dataset: An Open Benchmark for End-to-End Autonomous Parking}, 
      author={Kejia Gao and Liguo Zhou and Mingjun Liu and Alois Knoll},
      year={2025},
      eprint={2504.10812},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2504.10812}, 
}
```
