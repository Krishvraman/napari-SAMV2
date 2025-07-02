# napari-SAMV2

Napari plugin to use segment anything version 2.1 models from Meta.

Plugin made for segmenting 3d volumetric data or 3d time series data.

----------------------------------

## Installation

The plugin requires the following pre-requisite to be installed :

1. Python and pytorch versions

python>=3.10,torch>=2.5.1 and torchvision>=0.20.1 required

To install pytorch with your respective OS please visit - https://pytorch.org/get-started/locally/

2. SAM v2 installation from meta

Please refer https://github.com/facebookresearch/sam2

3. Install napari

python -m pip install "napari[all]"

Following is a sample conda environment installation with the above pre-req 

    conda create -n samv2_env python=3.10
    conda activate samv2_env
    pip3 install torch torchvision

    git clone https://github.com/facebookresearch/sam2.git && cd sam2
    pip install -e .

    python -m pip install "napari[all]"

    pip install napari-SAMV2


## Usage

Middle mouse click - positive point or keyboard shortcut "a"

Ctrl + Middle mouse click - negative point or keyboard shortcut "n"
