#!/bin/bash

set -x

container_workdir="/work/projects/polyullm/reallm.xyz/evalscope_dev"
container_image="/lustre/projects/polyullm/container/evalscope_eval+1.0a.sqsh"
container_mounts="/lustre/projects/polyullm:/lustre/projects/polyullm,/work/projects/polyullm:/work/projects/polyullm"

srun -n 1 -c 4 --container-image=${container_image} \
  --container-mounts=${container_mounts} \
  --container-workdir=${container_workdir} \
  --container-remap-root \ 
  --container-writable \
  --pty bash
