# trace generated using paraview version 6.1.1
from paraview.simple import *
from PIL import Image, ImageChops
import os
from pathlib import Path
import math
import argparse

#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

def paraview_save(exp_dir, percentages, save_path):
    # create a new 'XML Unstructured Grid Reader'
    u_0vtu = XMLUnstructuredGridReader(
        registrationName='u_0.vtu', 
        FileName=[f'{exp_dir}/percentage_{percentages[0]}/solution/u/u_0.vtu']
    )

    # create a new 'PVD Reader'
    upvd = PVDReader(
        registrationName='u.pvd', 
        FileName=f'{exp_dir}/percentage_{percentages[0]}/solution/u.pvd'
    )

    # get animation scene
    animationScene1 = GetAnimationScene()

    # update animation scene based on data timesteps
    animationScene1.UpdateAnimationUsingDataTimeSteps()

    # create a new 'PVD Reader'
    upvd_1 = PVDReader(
        registrationName='u.pvd', 
        FileName=f'{exp_dir}/percentage_{percentages[1]}/solution/u.pvd'
    )

    # create a new 'PVD Reader'
    upvd_2 = PVDReader(
        registrationName='u.pvd', 
        FileName=f'{exp_dir}/percentage_{percentages[2]}/solution/u.pvd'
    )

    # Properties modified on u_0vtu
    u_0vtu.TimeArray = 'None'

    # get active view
    renderView1 = GetActiveViewOrCreate('RenderView')
    renderView1.OrientationAxesVisibility = 0
    renderView1.CenterAxesVisibility = 0

    # show data in view
    u_0vtuDisplay = Show(u_0vtu, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    u_0vtuDisplay.Representation = 'Surface'

    # reset view to fit data
    renderView1.ResetCamera(False, 0.9)

    # changing interaction mode based on data extents
    renderView1.Set(
        InteractionMode='2D',
        CameraPosition=[0.4999999999999997, 0.5000000000000001, 3.3500000000000014],
        CameraFocalPoint=[0.4999999999999997, 0.5000000000000001, 0.0],
    )

    # get the material library
    materialLibrary1 = GetMaterialLibrary()

    # show data in view
    upvdDisplay = Show(upvd, renderView1, 'UnstructuredGridRepresentation')
    upvdDisplay.Representation = 'Surface'

    # show data in view
    upvd_1Display = Show(upvd_1, renderView1, 'UnstructuredGridRepresentation')
    upvd_1Display.Representation = 'Surface'

    # show data in view
    upvd_2Display = Show(upvd_2, renderView1, 'UnstructuredGridRepresentation')
    upvd_2Display.Representation = 'Surface'

    # update the view to ensure updated data information
    renderView1.Update()

    # Properties modified on renderView1
    renderView1.UseColorPaletteForBackground = 0
    renderView1.Background = [1.0, 1.0, 1.0]

    # set active source
    SetActiveSource(upvd)
    transform1 = Transform(registrationName='Transform1', Input=upvd)

    SetActiveSource(upvd_1)
    HideInteractiveWidgets(proxy=transform1.Transform)

    transform2 = Transform(registrationName='Transform2', Input=upvd_1)

    SetActiveSource(upvd_2)
    HideInteractiveWidgets(proxy=transform2.Transform)

    transform3 = Transform(registrationName='Transform3', Input=upvd_2)

    transform2.Transform.Translate = [2.2, 0.0, 0.0]
    transform2Display = Show(transform2, renderView1, 'UnstructuredGridRepresentation')
    transform2Display.Representation = 'Surface'
    Hide(upvd_1, renderView1)

    transform1.Transform.Translate = [1.1, 0.0, 0.0]
    transform1Display = Show(transform1, renderView1, 'UnstructuredGridRepresentation')
    transform1Display.Representation = 'Surface'
    Hide(upvd, renderView1)

    transform3.Transform.Translate = [3.3, 0.0, 0.0]
    transform3Display = Show(transform3, renderView1, 'UnstructuredGridRepresentation')
    transform3Display.Representation = 'Surface'
    Hide(upvd_2, renderView1)

    renderView1.Update()
    renderView1.AdjustZoom(0.6666666666666666)
    renderView1.AdjustZoom(0.6666666666666666)

    animationScene1.GoToLast()

    # transform3Display.Visibility = 0

    SetActiveSource(upvd)
    HideInteractiveWidgets(proxy=transform3.Transform)

    layout1 = GetLayout()
    layout1.SetSize(1488, 910)

    renderView1.Set(
        InteractionMode='2D',
        CameraPosition=[2.049030075049873, 0.3706227702554285, 3.3500000000000014],
        CameraFocalPoint=[2.049030075049873, 0.3706227702554285, 0.0],
        CameraParallelScale=1.5909902576697326,
    )

    SaveScreenshot(
        filename=os.path.join(save_path, "progression_Omega.png"),
        viewOrLayout=renderView1,
        location=16,
        ImageResolution=[4464, 654]
    )

from PIL import Image, ImageChops, ImageOps

def auto_crop_white_space(image_path, threshold=10):
    """
    Crop pure / near-white borders.
    threshold: how much deviation from pure white is still considered background.
    """
    try:
        im = Image.open(image_path).convert("RGB")
        # Invert so white becomes black (getbbox works on non-zero / non-black)
        inverted = ImageOps.invert(im)
        # Optional: make the crop a bit more tolerant
        # (boost small differences)
        diff = ImageChops.add(inverted, inverted, 2.0, -threshold)
        bbox = diff.getbbox()
        if bbox:
            cropped = im.crop(bbox)
            cropped.save(image_path)
            print(f"Successfully cropped empty space from {image_path}")
        else:
            print(f"No croppable border found in {image_path}")
    except Exception as e:
        print(f"Could not crop {image_path}: {e}")

def make_paraview_snapshots(exp_dir, percentages, save_path):
    paraview_save(exp_dir, percentages, save_path)
    auto_crop_white_space(os.path.join(save_path, "progression_Omega.png"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Save ParaView screenshots with auto-cropping.')
    parser.add_argument('--exp_dir', type=str, required=False, default=None, help='Path to experiment directory.')
    parser.add_argument('--percentages', nargs='+', type=str, default=['0.2', '0.5', '0.8'], help='List of percentages separated by space.')
    parser.add_argument('--save_path', type=str, required=False, default=None, help='Directory where screenshots will be saved.')
    args = parser.parse_args()

    percentages = [float(x) for x in args.percentages[0].strip('[]').split(',')]

    repo_root = Path(__file__).resolve().parent.parent.parent
    results_path = repo_root / "data" / "results"

    # Only look for the most recently modified run when an argument was omitted, so
    # that explicit paths work even before data/results exists.
    latest_run = None
    if args.exp_dir is None or args.save_path is None:
        candidates = [d for d in results_path.iterdir() if d.is_dir()] if results_path.is_dir() else []
        latest_run = max(candidates, key=lambda d: d.stat().st_mtime, default=None)
        if latest_run is None:
            raise SystemExit(
                f"No run directories found under {results_path}. "
                "Run an experiment first, or pass --exp_dir and --save_path explicitly."
            )

    exp_dir = latest_run if args.exp_dir is None else os.path.abspath(args.exp_dir)
    save_dir = (repo_root / "data" / "paraview_saves" / latest_run.name) if args.save_path is None else os.path.abspath(args.save_path)

    os.makedirs(save_dir, exist_ok=True)
    print(percentages)
    make_paraview_snapshots(str(exp_dir), percentages, str(save_dir))