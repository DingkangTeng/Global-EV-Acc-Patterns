# Overview

This repository contains all codes and (sample) dataset of the paper -
***From Points to Patterns: Global Spatial Accessibility and Equity in Public Electric Vehicle Charging***.

Note that the **full dataset** can be requested through our [Global EV Data Initiative](https://globalevdata.github.io/data.html).

## Requirements and Installation

The whole analysis-related codes should run with a **Python** environment, regardless of operating systems theoretically.
We successfully execute all the codes in Windows (Win 11) and Linux (Ubuntu 20) machines.
More detailed info is as below:

### Prerequisites

It is highly recommended to install and use the following versions of python/packages to run the codes:

- ``gdal`` == 3.12.2
- ``geopandas`` == 1.1.3
- ``iso3166`` == 2.1.1
- ``networkx`` == 3.6.1
- ``numpy`` == 2.5.0
- ``osmnx`` == 2.1.0
- ``pandas`` == 3.0.3
- ``pyproj`` == 3.7.2
- ``rasterio`` == 1.5.0
- ``scipy`` == 1.18.0
- ``Shapely`` == 2.1.2
- ``tqdm`` == 4.67.3

### Installation

It is highly recommended to download [AnaConda](https://www.anaconda.com) to create/manage Python environments.
You can create a new Python environment and install required aforementioned packages via both the GUI or Command Line.
   Typically, the installation should be prompt (around *10-20 min* from a "*clean*" machine to "*ready-to-use*" machine, but highly dependent on the Internet speed)

- via **Anaconda GUI**
  1. Open the Anaconda
  2. Find and click "*Environments*" at the left sidebar
  3. Click "*Create*" to create a new Python environment
  4. Select the created Python environment in the list, and then search and install all packages one by one.

- via **Command Line** (using ***Terminal*** for macOS machine and ***Anaconda Prompt*** for Windows machine, respectively)
  1. Create your new Python environment

     ```bash
     conda create --name <input_your_environment_name> python=3.14.3
     ```

  2. Activate the new environment

     ```bash
     conda activate <input_your_environment_name>
     ```

  3. Install all packages one by one

     ```bash
     conda install <package_name>=<specific_version>
     ```

### Project Structure

```text
┌─┬ analysis
│ ├── calPop.py, generateUrbanConnectingResults.py, points2Raster.py # code for data combination.
│ └── calDensity.py, urbanConnecting.py # code for density and OD pair calculation.
├── function # Scripts for data crawling and merging.
└── setting # Scripts for miscellaneous initialization.
```

## Usage

1. Git clone/download the repository to your local disk.
2. Unzip the full datasets in ``data`` (which can be provided upon request, see [Overview](https://github.com/DingkangTeng/Global-EV-Acc-Patterns?tab=readme-ov-file#overview))
3. Run ``main.ipynb script`` in ``code``
4. Outputs (including excel files and figures) will be stored based on the path in the first block.

## Contact

- Leave questions in [Issues on GitHub](https://github.com/DingkangTeng/Global-EV-Acc-Patterns/issues)
- Get in touch with the Corresponding Author: [Dr. Chengxiang Zhuge](mailto:chengxiang.zhuge@polyu.edu.hk)
or visit our research group website: [The TIP](https://thetipteam.editorx.io/website) for more information

## License

This repository is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
