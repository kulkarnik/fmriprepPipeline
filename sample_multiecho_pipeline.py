#!/usr/bin/env python
# Author: Kaustubh Kulkarni
# Date: Feb 20, 2020

"""

Here is an example script that utilizes the bids_pythonic module 
to build the BIDS formatted database and execute fmriprep using either
fmriprep-docker (for local usage) or singularity (minerva usage)

Examples of both single echo and multi echo are shown.

You can adapt this script for your use or build your own.

"""


import bids_pythonic as bp

if __name__ == "__main__":


    # Define your path names
    fs_license = '/Applications/freesurfer/license.txt'
    project_dir = '/Volumes/synapse/home/kulkak01/fmriprepPipeline/'
    bids_root = f"{project_dir}/multiecho_rawdata/bids_root/"
    output_dir = f"{project_dir}/multiecho_rawdata/fmriprep_output/"
    dicom_dir = f"{project_dir}/multiecho_rawdata/dicoms/"
    
    # Define your list of subjects
    # If 'sub-' is at the start of the subject string, it will be removed
    subs = ['sub-02']

    # Define dicom structure
    # Note that 'func' is a 2D list of lists, of all echos for each run
    multiecho = True
    anat = 'anat'
    func = [ 
        [
            'task-fish_run-1_echo-1',
            'task-fish_run-1_echo-2'
        ]
    ]

    # Define your task name
    task = 'fish'

    # Define the minerva options    
    image_location = f'{project_dir}' # where is the fmriprep.20.0.1.simg file located?
    batch_dir = f'{project_dir}/batch_dir/' # output directory for all batch scripts
    hpc_home = '/hpc/home/kulkak01/' # replace this with your own username on Minerva
    minerva_options = {
        'image_location': image_location,
        'batch_dir': batch_dir,
        'hpc_home': hpc_home
    }

    # This method creates the bids root directory
    bp.create_bids_root(bids_root)

    for name in subs:
        setup = bp.SetupBIDSPipeline(dicom_dir, name, anat, func, task, bids_root, ignore=True, multiecho=multiecho)
        setup.validate(multiecho=multiecho)
        setup.create_bids_hierarchy()
        setup.convert(multiecho=multiecho)
        setup.update_json()

    fp_singularity = bp.FmriprepSingularityPipeline(subs, bids_root, output_dir, fs_license, minerva_options, multiecho=multiecho)
    fp_singularity.create_singularity_batch()
    #fp_singularity.run_singularity_batch()