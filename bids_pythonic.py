#!/usr/bin/env python
# Author: Kaustubh Kulkarni
# Date: Feb 20, 2020

import argparse
import json
import os
import subprocess
import shutil
import logging
import datetime

class FmriprepPipeline(object):

    def __init__(self, params, pipeline_dir=os.getcwd()):
        if not os.path.exists(pipeline_dir):
            os.makedirs(pipeline_dir)
        self.pipeline_dir = pipeline_dir

        x = datetime.datetime.now()
        timestamp = x.strftime("%m-%d_%H%M")
        self.logfile = f'{self.pipeline_dir}/log_{timestamp}.txt'
        logging.basicConfig(format='%(module)s - %(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

        self.pdict = params
        self.root_exists = False
        self.anat_path = ""
        self.func_path = ""
        self.anat_name = ""
        self.func_name = []
            

    def validate(self):
        logging.info('Validating parameters.....')

        # Validate parameters dictionary
        root_path = self.pdict['root']
        if os.path.isdir(root_path):
            logging.warning('Root Exists! Not overwriting.')
            self.root_exists = True
        
        if os.path.isdir(f'{self.pdict["root"]}/sub-{self.pdict["name"]}'):
            if self.pdict['overwrite'] == 'true':
                logging.warning(f'Overwrite option selected! Removing subject {self.pdict["name"]}')
                shutil.rmtree(f'{self.pdict["root"]}/sub-{self.pdict["name"]}')
            else:
                logging.error(f"{self.pdict['name']}' exists! Try a different subject name, or delete existing folder.")
                raise OSError(f"'{self.pdict['name']}' exists! Try a different subject name, or delete existing folder.")

        if not os.path.isdir(self.pdict['anat']):
            logging.error(f"'{self.pdict['anat']}' does not exist! Input a valid anatomical DICOM directory.")
            raise OSError(f"'{self.pdict['anat']}' does not exist! Input a valid anatomical DICOM directory.")

        for func in self.pdict['func']:
            if not os.path.isdir(func):
                logging.error(f"'{func}' does not exist! Input a valid functional DICOM directory.")
                raise OSError(f"'{func}' does not exist! Input a valid functional DICOM directory.")
    
        # Validate fmriprep-docker requirements

        # Validate motion regression requirements

        logging.info('Validated!')


    def create_bids_hierarchy(self):
        logging.info('Creating BIDS hierarchy.....')

        # Create root directory
        # Create dataset_description.json and README
        if not self.root_exists:
            os.makedirs(self.pdict['root'])
            ds_desc =   {
                    "Name": self.pdict['description'],
                    "BIDSVersion": "1.0.1",
                    "License": "CC0",
                    "Authors": [
                        "Kaustubh Kulkarni",
                        "Matt Schafer"
                    ],
                    "DatasetDOI": "10.0.2.3/dfjj.10"
                    }
            dd_path = f'{self.pdict["root"]}/dataset_description.json'
            with open(dd_path, 'w') as outfile:
                json.dump(ds_desc, outfile)
            readme_path = f'{self.pdict["root"]}/README'
            with open(readme_path, 'w') as outfile:
                outfile.write('This is a README')

        # Create subject directory
        sub_path = f'{self.pdict["root"]}/sub-{self.pdict["name"]}'
        os.makedirs(sub_path)

        # Create anat and func directories (if in params)
        if self.pdict['anat']:
            self.anat_path = f'{sub_path}/anat/'
            os.makedirs(self.anat_path)

        if self.pdict['func']:
            self.func_path = f'{sub_path}/func/'
            os.makedirs(self.func_path)

        logging.info("Completed!")

    def convert(self):
        # Run dcm2niix for anatomical DICOM and rename
        logging.info('Converting anatomical DICOMs to NIFTI and renaming.....')
        self.anat_name = f'sub-{self.pdict["name"]}_T1w'
        command = ['dcm2niix', '-z', 'n', '-f', self.anat_name, '-b', 'y', '-o', self.anat_path, self.pdict['anat']]
        #print(command)
        process = subprocess.run(command)
        logging.info('Completed!')


        # Run dcm2niix for every functional DICOM and rename
        logging.info('Converting functional DICOMs to NIFTI and renaming.....')
        run_counter = 1
        for func_input in self.pdict['func']:
            func_name = f'sub-{self.pdict["name"]}_task-{self.pdict["task"]}_run-{str(run_counter)}_bold'
            self.func_name.append(func_name)
            command = ['dcm2niix', '-z', 'n', '-f', func_name, '-b', 'y', '-o', self.func_path, func_input]
            #print(command)
            process = subprocess.run(command)
            run_counter += 1
        logging.info('Completed!')


    def update_json(self):
        # Add TaskName field to BIDS functional NIFTI sidecars
        logging.info('Updating functional NIFTI sidecars.....')
        for func in self.func_name:
            with open(f'{self.func_path}/{func}.json') as json_file:
                data = json.load(json_file)
                data['TaskName'] = self.pdict["task"]

            with open(f'{self.func_path}/{func}.json', 'w') as outfile:
                json.dump(data,outfile)
        logging.info('Completed!')


# Standalone module method
def run_fmriprep(subs, bids_root, output, fs_license, freesurfer=False, minerva=False, minerva_options = {}):
    # Run fmriprep-docker command
    if not minerva:
        logging.info('Executing fmriprep-docker command')
        command = ['fmriprep-docker', bids_root, output, 'participant', '--fs-license-file', fs_license]
        if not freesurfer:
            command.append('--fs-no-reconall')
        logging.info(command)
        subprocess.run(command)

    elif minerva:
        logging.info('Setting up fmriprep command through Singularity for Minerva')
        
        # if not os.path.isfile(f'{minerva_options["image_directory"]}/fmriprep-20.0.1.simg'):
        #     logging.error('fmriprep image does not exist in the given directory!')
        #     raise OSError('fmriprep image does not exist in the given directory!')

        logging.info('Creating batch directory for subject scripts')
        batch_dir = f'{minerva_options["batch_dir"]}'
        if not os.path.isdir(batch_dir):
            os.makedirs(batch_dir)
        if not os.path.isdir(f'{batch_dir}/batchoutput'):
            os.makedirs(f'{batch_dir}/batchoutput')

        for sub in subs:
            sub_batch_script = f'{batch_dir}/sub-{sub}.sh'
            with open(sub_batch_script, 'w') as f:
                lines = [
                f'#!/bin/bash\n\n',
                f'#BSUB -J fmriprep_sub-{sub}\n',
                f'#BSUB -P acc_guLab\n',
                f'#BSUB -q private\n',
                f'#BSUB -n 4\n',
                f'#BSUB -W 20:00\n',
                f'#BSUB -R rusage[mem=16000]\n',
                f'#BSUB -o {batch_dir}/batchoutput/nodejob-fmriprep-sub-{sub}.out\n',
                f'#BSUB -L /bin/bash\n\n',
                f'ml singularity/3.2.1\n\n',
                f'cd {minerva_options["image_directory"]}\n',
                ]
                f.writelines(lines)

                command = f'singularity run --home {minerva_options["hpc_home"]} --cleanenv fmriprep-20.0.1.simg {bids_root} {output} participant --participant-label {sub} --notrack --fs-license-file {fs_license}'
                if not freesurfer:
                   command = " ".join([command, '--fs-no-reconall'])
                f.write(command) 


def motionreg(subs):
    # Run either GLM regression or ART repair for motion
    pass
