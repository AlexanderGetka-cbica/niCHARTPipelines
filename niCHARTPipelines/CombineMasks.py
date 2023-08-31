import numpy as np
import nibabel as nib
from nipype.interfaces.image import Reorient
from nibabel.orientations import axcodes2ornt, ornt_transform, inv_ornt_aff

## Find bounding box for the foreground values in img, with a given padding percentage
def calc_bbox_with_padding(img, perc_pad = 10):
    
    ## Output is the coordinates of the bounding box
    bcoors = np.zeros([3,2], dtype=int)
    
    ## Find coors in each axis
    for sel_axis in [0, 1, 2]:
    
        ## Get axes other than the selected
        other_axes = [0, 1, 2]
        other_axes.remove(sel_axis)
        
        ## Get img dim in selected axis
        dim = img.shape[sel_axis]
        
        ## Find bounding box (index of first and last non-zero slices)
        nonzero = np.any(img, axis = tuple(other_axes))
        bbox= np.where(nonzero)[0][[0,-1]]    
        
        ## Add padding
        size_pad = int(np.round((bbox[1] - bbox[0]) * perc_pad / 100))
        b_min = int(np.max([0, bbox[0] - size_pad]))
        b_max = int(np.min([dim, bbox[1] + size_pad]))
        
        bcoors[sel_axis, :] = [b_min, b_max]
    
    return bcoors

def apply_combine(in_img_name, icv_img_name, out_img_name):
    '''Combine icv and muse masks.
    '''
    ## Read input images
    nii_in = nib.load(in_img_name)
    nii_icv = nib.load(icv_img_name)

    img_in = nii_in.get_fdata()
    img_icv = nii_icv.get_fdata()
    
    ################################
    ## INFO: nnunet hallucinated on images with large FOV. To solve this problem
    ##       we added pre/post processing steps to crop initial image around ICV 
    ##       mask before sending to DLMUSE
    ##
    ## MUSE image (img_in) may be cropped. Pad it to initial image size
    bcoors = calc_bbox_with_padding(img_icv)
    img_out = img_icv * 0
    img_out[bcoors[0,0]:bcoors[0,1], bcoors[1,0]:bcoors[1,1], bcoors[2,0]:bcoors[2,1]] = img_in
    ################################

    # Merge masks : Add a new label (1) to MUSE for foreground voxels in ICV that is not in MUSE
    #  this label will mainly represent cortical CSF
    img_out[(img_out==0) & (img_icv>0)] = 1
    
    img_out = img_out.astype(int)

    ## Save out image
    nii_out = nib.Nifti1Image(img_out, nii_in.affine, nii_in.header)    
    nii_out.to_filename(out_img_name)