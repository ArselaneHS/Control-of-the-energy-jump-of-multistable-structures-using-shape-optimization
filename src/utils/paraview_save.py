# trace generated using paraview version 6.1.0
#import paraview
#paraview.compatibility.major = 6
#paraview.compatibility.minor = 1

#### import the simple module from the paraview
from paraview.simple import *
from PIL import Image, ImageChops
import os
from pathlib import Path
import math

#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

def tilt_camera(focal_point, distance, tilt_deg=100):
    """
    Given a flat top-down focal_point [x, y, 0] and camera distance along z,
    return a CameraPosition tilted by tilt_deg around the x-axis so the
    z-extrusion becomes visible, while keeping the same x,y framing.
    (Math unchanged — this is a correct rotation of (0,0,distance) about x.)
    """
    angle = math.radians(tilt_deg)
    x, y, z_focal = focal_point
    cam_y = y - distance * math.sin(angle)
    cam_z = z_focal + distance * math.cos(angle)
    return [x, cam_y, cam_z]


def set_camera(renderView1, focal_point, distance, tilt_deg, parallel_scale, is_3d=False,
               y_extent=1.0, z_extent=None, margin=1.0):
    """
    Single place that configures the camera for either the flat 2D view
    or the tilted 3D view, so both branches share the same calibration logic.

    y_extent / z_extent: approximate world-space size of the domain in y
        and of the warp/extrusion in z. Used to compensate CameraParallelScale
        so the tilt doesn't clip the top of the warped surface.
    margin: extra multiplicative safety factor (e.g. 1.05-1.15) on top of the
        computed compensation, in case the analytic estimate undershoots.
    """
    CameraViewUp = [0, 1, 0]

    if not is_3d:
        renderView1.Set(
            InteractionMode='2D',
            CameraPosition=[focal_point[0], focal_point[1], distance],
            CameraFocalPoint=focal_point,
            CameraParallelScale=parallel_scale,
        )
        renderView1.CameraParallelProjection = 1
    else:
        renderView1.InteractionMode = '3D'
        renderView1.CameraParallelProjection = 1        # <-- the fix
        renderView1.CameraViewUp = CameraViewUp
        renderView1.CameraFocalPoint = focal_point
        renderView1.CameraPosition = tilt_camera(focal_point, distance, tilt_deg=tilt_deg)

        # Compensate for the extra vertical extent revealed by the tilt.
        theta = math.radians(tilt_deg)
        if z_extent is not None and y_extent > 0:
            compensation = abs(math.cos(theta)) + (z_extent / y_extent) * abs(math.sin(theta))
        else:
            compensation = 1.0
        renderView1.CameraParallelScale = parallel_scale * compensation * margin
        


def paraview_save(pvd_path, save_path, is_3d = False, fixed_min=None, fixed_max=None):
    # create a new 'PVD Reader'
    upvd = PVDReader(registrationName='u.pvd', FileName=pvd_path)

    # get animation scene
    animationScene1 = GetAnimationScene()

    # update animation scene based on data timesteps
    animationScene1.UpdateAnimationUsingDataTimeSteps()

    # get active view
    renderView1 = GetActiveViewOrCreate('RenderView')

    # show data in view
    upvdDisplay = Show(upvd, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    upvdDisplay.Representation = 'Surface'

    # reset view to fit data
    renderView1.ResetCamera(False, 0.9)

    #changing interaction mode based on data extents
    # renderView1.Set(
    #     InteractionMode='2D',
    #     CameraPosition=[0.4999999999999997, 0.5000000000000001, 3.3500000000000014],
    #     CameraFocalPoint=[0.4999999999999997, 0.5000000000000001, 0.0],
    # )

    # renderView1.InteractionMode = '2D'
    # renderView1.CameraPosition = [0.4999999999999997, 0.5000000000000001, 3.3500000000000014]
    # renderView1.CameraFocalPoint = [0.4999999999999997, 0.5000000000000001, 0.0]

    focal_point = [0.4999999999999997, 0.5000000000000001, 0.5]
    distance = 3.3500000000000014
    tilt_deg = 3.0
    CameraViewUp = [0.005, 0, 1]

    if not is_3d:
        renderView1.Set(
            InteractionMode='2D',
            CameraPosition=[focal_point[0], focal_point[1], distance],
            CameraFocalPoint=focal_point,
        )
    else:
        renderView1.InteractionMode = '3D'
        renderView1.CameraParallelProjection = 1
        renderView1.CameraViewUp = CameraViewUp
        renderView1.CameraFocalPoint = focal_point
        renderView1.CameraPosition = tilt_camera(focal_point, distance, tilt_deg=tilt_deg)
        
            # get the material library
    materialLibrary1 = GetMaterialLibrary()

    # update the view to ensure updated data information
    renderView1.Update()

    # create a new 'Warp By Vector'
    warpByVector1 = WarpByVector(registrationName='WarpByVector1', Input=upvd)

    # set active source
    SetActiveSource(upvd)

    # create a new 'Warp By Vector'
    warpByVector2 = WarpByVector(registrationName='WarpByVector2', Input=upvd)

    # set active source
    SetActiveSource(upvd)

    # create a new 'Warp By Vector'
    warpByVector3 = WarpByVector(registrationName='WarpByVector3', Input=upvd)

    # set active source
    SetActiveSource(warpByVector2)

    # set active source
    SetActiveSource(warpByVector3)

    # show data in view
    warpByVector1Display = Show(warpByVector1, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    warpByVector1Display.Representation = 'Surface'

    # hide data in view
    Hide(upvd, renderView1)

    # Properties modified on warpByVector2
    warpByVector2.Vectors = ['POINTS', 'u_2']

    # show data in view
    warpByVector2Display = Show(warpByVector2, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    warpByVector2Display.Representation = 'Surface'

    # hide data in view
    Hide(upvd, renderView1)

    # Properties modified on warpByVector3
    warpByVector3.Vectors = ['POINTS', 'u_3']

    # show data in view
    warpByVector3Display = Show(warpByVector3, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    warpByVector3Display.Representation = 'Surface'

    # hide data in view
    Hide(upvd, renderView1)

    # update the view to ensure updated data information
    renderView1.Update()

    # set active source
    SetActiveSource(upvd)

    # show data in view
    upvdDisplay = Show(upvd, renderView1, 'UnstructuredGridRepresentation')

    # set active source
    SetActiveSource(warpByVector1)

    # set scalar coloring
    ColorBy(warpByVector1Display, ('POINTS', 'u_1', 'Magnitude'))

    # rescale color and/or opacity maps used to include current data range
    warpByVector1Display.RescaleTransferFunctionToDataRange(True, False)

    # show color bar/color legend
    warpByVector1Display.SetScalarBarVisibility(renderView1, True)

    # get color transfer function/color map for 'u_1'
    u_1LUT = GetColorTransferFunction('u_1')

    # get opacity transfer function/opacity map for 'u_1'
    u_1PWF = GetOpacityTransferFunction('u_1')

    # get 2D transfer function for 'u_1'
    u_1TF2D = GetTransferFunction2D('u_1')

    # set active source
    SetActiveSource(warpByVector2)

    # set scalar coloring
    ColorBy(warpByVector2Display, ('POINTS', 'u_2', 'Magnitude'))

    # rescale color and/or opacity maps used to include current data range
    warpByVector2Display.RescaleTransferFunctionToDataRange(True, False)

    # show color bar/color legend
    warpByVector2Display.SetScalarBarVisibility(renderView1, True)

    # get color transfer function/color map for 'u_2'
    u_2LUT = GetColorTransferFunction('u_2')

    # get opacity transfer function/opacity map for 'u_2'
    u_2PWF = GetOpacityTransferFunction('u_2')

    # get 2D transfer function for 'u_2'
    u_2TF2D = GetTransferFunction2D('u_2')

    # set active source
    SetActiveSource(warpByVector3)

    # set scalar coloring
    ColorBy(warpByVector3Display, ('POINTS', 'u_3', 'Magnitude'))

    # rescale color and/or opacity maps used to include current data range
    warpByVector3Display.RescaleTransferFunctionToDataRange(True, False)

    # show color bar/color legend
    warpByVector3Display.SetScalarBarVisibility(renderView1, True)

    # get color transfer function/color map for 'u_3'
    u_3LUT = GetColorTransferFunction('u_3')

    # get opacity transfer function/opacity map for 'u_3'
    u_3PWF = GetOpacityTransferFunction('u_3')

    # get 2D transfer function for 'u_3'
    u_3TF2D = GetTransferFunction2D('u_3')


    # set scalar coloring for u_1
    ColorBy(warpByVector1Display, ('POINTS', 'u_1', 'Magnitude'))
    warpByVector1Display.RescaleTransferFunctionToDataRange(True, False)  # keep this to initialize
    warpByVector1Display.SetScalarBarVisibility(renderView1, True)
    u_1LUT = GetColorTransferFunction('u_1')
    u_1PWF = GetOpacityTransferFunction('u_1')
    u_1TF2D = GetTransferFunction2D('u_1')

    # set scalar coloring for u_2
    ColorBy(warpByVector2Display, ('POINTS', 'u_2', 'Magnitude'))
    warpByVector2Display.RescaleTransferFunctionToDataRange(True, False)
    warpByVector2Display.SetScalarBarVisibility(renderView1, True)
    u_2LUT = GetColorTransferFunction('u_2')
    u_2PWF = GetOpacityTransferFunction('u_2')
    u_2TF2D = GetTransferFunction2D('u_2')

    # set scalar coloring for u_3
    ColorBy(warpByVector3Display, ('POINTS', 'u_3', 'Magnitude'))
    warpByVector3Display.RescaleTransferFunctionToDataRange(True, False)
    warpByVector3Display.SetScalarBarVisibility(renderView1, True)
    u_3LUT = GetColorTransferFunction('u_3')
    u_3PWF = GetOpacityTransferFunction('u_3')
    u_3TF2D = GetTransferFunction2D('u_3')

    # --- Fix color range ---
    if fixed_max is not None:
        for lut, pwf in [(u_1LUT, u_1PWF), (u_2LUT, u_2PWF), (u_3LUT, u_3PWF)]:
            lut.RescaleTransferFunction(fixed_min, fixed_max)
            pwf.RescaleTransferFunction(fixed_min, fixed_max)

        # CRITICAL: disable auto-rescaling on every display object
        for display in [warpByVector1Display, warpByVector2Display, warpByVector3Display]:
            display.SetScalarBarVisibility(renderView1, False)

        # Lock the LUTs so they don't auto-update on Show()
        u_1LUT.AutomaticRescaleRangeMode = 'Never'
        u_2LUT.AutomaticRescaleRangeMode = 'Never'
        u_3LUT.AutomaticRescaleRangeMode = 'Never'

    # After all three LUTs are defined, force ALL colormap properties explicitly
    for lut in [u_1LUT, u_2LUT, u_3LUT]:
        # Force the colormap by name
        lut.ApplyPreset('Cool to Warm', True)  # or 'Blue to Red Rainbow', etc.
        # Lock rescaling behavior
        lut.AutomaticRescaleRangeMode = 'Never'
        if fixed_min is not None and fixed_max is not None:
            lut.RescaleTransferFunction(fixed_min, fixed_max)
    if fixed_min is not None and fixed_max is not None:
        for pwf in [u_1PWF, u_2PWF, u_3PWF]:
            pwf.RescaleTransferFunction(fixed_min, fixed_max)

    # set active source
    SetActiveSource(warpByVector1)

    # create a new 'Transform'
    transform1 = Transform(registrationName='Transform1', Input=warpByVector1)

    # set active source
    SetActiveSource(warpByVector2)

    # toggle interactive widget visibility (only when running from the GUI)
    HideInteractiveWidgets(proxy=transform1.Transform)

    # create a new 'Transform'
    transform2 = Transform(registrationName='Transform2', Input=warpByVector2)

    # set active source
    SetActiveSource(warpByVector3)

    # toggle interactive widget visibility (only when running from the GUI)
    HideInteractiveWidgets(proxy=transform2.Transform)

    # create a new 'Transform'
    transform3 = Transform(registrationName='Transform3', Input=warpByVector3)

    # Properties modified on transform3.Transform
    transform3.Transform.Translate = [3.35, 0.0, 0.0]

    # show data in view
    transform3Display = Show(transform3, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    transform3Display.Representation = 'Surface'

    # hide data in view
    Hide(warpByVector3, renderView1)

    # show color bar/color legend
    transform3Display.SetScalarBarVisibility(renderView1, True)

    # Properties modified on transform1.Transform
    transform1.Transform.Translate = [1.05, 0.0, 0.0]

    # show data in view
    transform1Display = Show(transform1, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    transform1Display.Representation = 'Surface'

    # hide data in view
    Hide(warpByVector1, renderView1)

    # show color bar/color legend
    transform1Display.SetScalarBarVisibility(renderView1, True)

    # Properties modified on transform2.Transform
    transform2.Transform.Translate = [2.2, 0.0, 0.0]

    # show data in view
    transform2Display = Show(transform2, renderView1, 'UnstructuredGridRepresentation')

    # trace defaults for the display properties.
    transform2Display.Representation = 'Surface'

    # hide data in view
    Hide(warpByVector2, renderView1)

    # show color bar/color legend
    transform2Display.SetScalarBarVisibility(renderView1, True)

    # update the view to ensure updated data information
    renderView1.Update()

    # set active source
    SetActiveSource(upvd)

    # toggle interactive widget visibility (only when running from the GUI)
    HideInteractiveWidgets(proxy=transform3.Transform)

    # Properties modified on renderView1
    renderView1.UseColorPaletteForBackground = 0

    # Properties modified on renderView1
    renderView1.Background = [1.0, 1.0, 1.0]

    # Properties modified on renderView1
    renderView1.OrientationAxesVisibility = 0

    # set active source
    SetActiveSource(transform1)

    # toggle interactive widget visibility (only when running from the GUI)
    ShowInteractiveWidgets(proxy=transform1.Transform)

    # hide color bar/color legend
    transform1Display.SetScalarBarVisibility(renderView1, False)

    # set active source
    SetActiveSource(transform2)

    # toggle interactive widget visibility (only when running from the GUI)
    HideInteractiveWidgets(proxy=transform1.Transform)

    # toggle interactive widget visibility (only when running from the GUI)
    ShowInteractiveWidgets(proxy=transform2.Transform)

    # hide color bar/color legend
    transform2Display.SetScalarBarVisibility(renderView1, False)

    # set active source
    SetActiveSource(transform3)

    # toggle interactive widget visibility (only when running from the GUI)
    HideInteractiveWidgets(proxy=transform2.Transform)

    # toggle interactive widget visibility (only when running from the GUI)
    ShowInteractiveWidgets(proxy=transform3.Transform)

    # hide color bar/color legend
    transform3Display.SetScalarBarVisibility(renderView1, False)

    # set active source
    SetActiveSource(upvd)

    # toggle interactive widget visibility (only when running from the GUI)
    HideInteractiveWidgets(proxy=transform3.Transform)

    # get layout
    layout1 = GetLayout()

    # split cell
    layout1.SplitVertical(0, 0.5)

    # set active view
    SetActiveView(None)

    # set active view
    SetActiveView(renderView1)

    renderView1.AdjustZoom(1.5)

    # layout/tab size in pixels
    layout1.SetSize(1488, 218)

    # current camera placement for renderView1
    focal_point2 = [2.1783325171138674, 0.47475963339366994, 0.0]
    distance2 = 3.3500000000000014

    if not is_3d:
        renderView1.Set(
            InteractionMode='2D',
            CameraPosition=[focal_point2[0], focal_point2[1], distance2],
            CameraFocalPoint=focal_point2,
            CameraParallelScale=0.6901833588901498,
        )
    else:
        renderView1.InteractionMode = '3D'
        renderView1.CameraParallelProjection = 1
        renderView1.CameraViewUp = CameraViewUp
        renderView1.CameraFocalPoint = focal_point2
        renderView1.CameraPosition = tilt_camera(focal_point2, distance2, tilt_deg=tilt_deg)
        renderView1.CameraParallelScale = 0.6901833588901498 * (abs(math.cos(math.radians(tilt_deg))) + 0.35 * abs(math.sin(math.radians(tilt_deg))))
        
            # After all Show(transform...) calls and renderView1.Update()
    if fixed_max is not None:
        for lut, pwf in [(u_1LUT, u_1PWF), (u_2LUT, u_2PWF), (u_3LUT, u_3PWF)]:
            lut.RescaleTransferFunction(fixed_min, fixed_max)
            pwf.RescaleTransferFunction(fixed_min, fixed_max)

        renderView1.Update()

    # save screenshot
    SaveScreenshot(filename=save_path+"/Omega0.png", viewOrLayout=renderView1, location=16, ImageResolution=[4464, 654])

    animationScene1.GoToLast()

    # layout/tab size in pixels
    layout1.SetSize(1488, 218)

    # current camera placement for renderView1
    focal_point2 = [2.1783325171138674, 0.47475963339366994, 0.0]
    distance2 = 3.3500000000000014

    if not is_3d:
        renderView1.Set(
            InteractionMode='2D',
            CameraPosition=[focal_point2[0], focal_point2[1], distance2],
            CameraFocalPoint=focal_point2,
            CameraParallelScale=0.6901833588901498,
        )
    else:
        renderView1.InteractionMode = '3D'
        renderView1.CameraParallelProjection = 1
        renderView1.CameraViewUp = CameraViewUp
        renderView1.CameraFocalPoint = focal_point2
        renderView1.CameraPosition = tilt_camera(focal_point2, distance2, tilt_deg=tilt_deg)
        renderView1.CameraParallelScale = 0.6901833588901498 * (abs(math.cos(math.radians(tilt_deg))) + 0.35 * abs(math.sin(math.radians(tilt_deg))))

    # save screenshot
    SaveScreenshot(filename=save_path+"/OmegaT.png", viewOrLayout=renderView1, location=16, ImageResolution=[4464, 654])

def auto_crop_white_space(image_path):
    try:
        im = Image.open(image_path)
        # Create a solid white background comparison image
        bg = Image.new(im.mode, im.size, (255, 255, 255))
        # Find the difference between your image and pure white
        diff = ImageChops.difference(im, bg)
        # Get the bounding box of the non-white content
        bbox = diff.getbbox()
        if bbox:
            # Crop and overwrite the image with the tight bounds
            cropped = im.crop(bbox)
            cropped.save(image_path)
            print(f"Successfully cropped empty space from {image_path}")
    except Exception as e:
        print(f"Could not crop {image_path}: {e}")

def make_paraview_snapshots(pvd_path, save_path, is_3d):
    paraview_save(pvd_path, save_path, is_3d=is_3d)
    auto_crop_white_space(save_path+"/Omega0.png")
    auto_crop_white_space(save_path+"/OmegaT.png")
    
if __name__ == "__main__":


    import argparse
    parser = argparse.ArgumentParser(description='Save Paraview screenshots with auto-cropping.')
    parser.add_argument('--pvd_path', type=str, required=False, default=None, help='Path to the .pvd file to load in Paraview.')
    parser.add_argument('--save_path', type=str, required=False, default=None, help='Directory where the screenshots will be saved.')
    parser.add_argument('--is_3d', action="store_true", required=False, default=False, help='Directory where the screenshots will be saved.')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    results_path = repo_root / "data" / "results"

    # Only fall back to "most recently modified run" for the arguments that were not
    # given; resolving it eagerly made an explicit --pvd_path fail whenever
    # data/results did not exist yet.
    latest_run = None
    if args.pvd_path is None or args.save_path is None:
        candidates = [d for d in results_path.iterdir() if d.is_dir()] if results_path.is_dir() else []
        latest_run = max(candidates, key=lambda d: d.stat().st_mtime, default=None)
        if latest_run is None:
            raise SystemExit(
                f"No run directories found under {results_path}. "
                "Run an experiment first, or pass --pvd_path and --save_path explicitly."
            )

    if args.pvd_path is None:
        abs_pvd_path = latest_run / "solution" / "u.pvd"
    else:
        abs_pvd_path = os.path.abspath(args.pvd_path)
    if args.save_path is None:
        abs_save_dir = repo_root / "data" / "paraview_saves" / latest_run.name
    else:
        abs_save_dir = os.path.abspath(args.save_path)

    os.makedirs(abs_save_dir, exist_ok=True)

    make_paraview_snapshots(str(abs_pvd_path), str(abs_save_dir), args.is_3d)
