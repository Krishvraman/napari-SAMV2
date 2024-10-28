# napari-SAMV2

Napari plugin to use segment anything version 2 models from Meta.

Plugin primarily made for segmenting 3d volumetric data or 3d time series data.

----------------------------------


## Installation

Pre-requisite of samv2 installation needed: --- Our current plugin supports only sam v 2.0  not 2.1.   So, we need to pull the SAM repo around september 15 ,2024 (last update of SAM2.0)

    git clone https://github.com/facebookresearch/segment-anything-2.git
    cd segment-anything-2
    git rev-list -n 1 --before="2024-09-15" HEAD
    git checkout <commit_hash>
    pip install -e .

You can install `napari-SAMV2` via [pip]:

    pip install napari-SAMV2

******

The plugin and installation tested with python 3.10 in conda environment with pytorch-cuda=12.1

conda environment with example :

    conda create -n samv2_env python=3.10
    conda activate samv2_env
    conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
    python -m pip install "napari[all]"

    git clone https://github.com/facebookresearch/segment-anything-2.git
    cd segment-anything-2
    git rev-list -n 1 --before="2024-09-15" HEAD
    
    git checkout <commit_hash>
    pip install -e .
    pip install napari-SAMV2    

*****

## Usage

Middle mouse click - positive point

Ctrl + Middle mouse click - negative point

Time Series Segmentation :

![samv2_time_series_demo](https://github.com/user-attachments/assets/078ca2bb-3016-4257-ac7c-c3cde8f9d125)



Volume Segmentation :

![samv2_volume_segmentation](https://github.com/user-attachments/assets/af05fcc4-a60d-44e8-ae05-70764d96e828)



Reference :

Example Data from in demo videos from,
Cell tracking challenge - https://celltrackingchallenge.net/ 
FlyEM project - https://www.janelia.org/project-team/flyem/hemibrain


## License

Distributed under the terms of the [BSD-3] license,
"napari-SAMV2" is free and open source software



## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/Krishvraman/napari-SAMV2/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
