import numpy as np
import dearcygui as dcg
from dearcygui.utils.asyncio_helpers import AsyncPoolExecutor, AsyncThreadPoolExecutor, run_viewport_loop
import asyncio
import os  #test committ - another test commit

# Set the title of the window
title = "DearCyGui - First Plot"

# Main function to run the demo
C = dcg.Context()
loop = asyncio.get_event_loop()
asyncio.set_event_loop(loop)
C.queue = AsyncPoolExecutor()
# refresh only when needed
C.viewport.wait_for_input = True
# Set an icon for the viewport (must be set before initializing the viewport)
#=C.viewport.icon = create_demo_icon()  #need to dig up my toaster icon

# Set some app metadata (completly optional)
dcg.os.set_application_metadata(
    name="DearCyGui porting",
    version="0.1.0",
    identifier="dearcygui.demo",
    creator="DearCyGui Team",
    copyright="MIT",
    url="https://github.com/DearCyGui/Demos",
    type="application")

# --- White theme setup from Bearing_Tester0_8_6.py ---
viewport_theme = dcg.ThemeColorImGui(C,
    border_shadow=(0.960784375667572, 0.960784375667572, 0.960784375667572, 0.0),
    window_bg=(0.9490196704864502, 0.9058824181556702, 0.9058824181556702, 0.9411765336990356),
    title_bg=(0.9803922176361084, 0.9803922176361084, 0.9803922176361084, 1.0),
    text=(0.1, 0.9, 0.14509804546833038, 1.0),
    menu_bar_bg=(0.8823530077934265, 0.9019608497619629, 0.9843137860298157, 1.0),
    popup_bg=(0.8666667342185974, 0.8901961445808411, 0.8705883026123047, 0.9411765336990356))
plot_theme = dcg.ThemeColorImPlot(C,
    axis_grid=(0.07450980693101883, 0.06666667014360428, 0.06666667014360428, 0.250980406999588)
)
theme = dcg.ThemeList(C)
theme.children = [viewport_theme, plot_theme]
# --- End white theme setup ---

# Initialize the viewport with the white theme
C.viewport.initialize(title=title, width=950, height=750) #, theme=theme)
# add a mouse click callback for the plot
async def mouse_callback(sender, target, data):
    #print('Mouse coordinates:', plot.X1.mouse_coord, plot.Y1.mouse_coord)
    x_value.value = f"X: {plot.X1.mouse_coord:.2f}"
    y_value.value = f"Y: {plot.Y1.mouse_coord:.2f}"

async def clicked_callback(sender, target, data):
    print('Mouse clicked at:', plot.X1.mouse_coord, plot.Y1.mouse_coord)

def lock_axes(sender, target, data):
    if plot.X1.lock_min or plot.X1.lock_max or plot.Y1.lock_min or plot.Y1.lock_max:
        print('Unlocking axes')
        plot.X1.lock_min = False
        plot.X1.lock_max = False
        plot.Y1.lock_min = False
        plot.Y1.lock_max = False
        lock_axes_button.label = "Lock axes"
    else:
        print('Locking axes')
        plot.X1.lock_min = True
        plot.X1.lock_max = True
        plot.Y1.lock_min = True
        plot.Y1.lock_max = True
        lock_axes_button.label = "Unlock axes"


# create a main window
with dcg.Window(C, label="Main Window",primary=True, width='viewport.width', height='viewport.height') as main_window:
    # create a menu bar
    with dcg.MenuBar(C):
        # create a file menu
        with dcg.Menu(C, label="File"):
            # create a new file menu item
            dcg.MenuItem(C, label="New", callback=lambda s, t, d: print("New File"))
            # create an open file menu item
            dcg.MenuItem(C, label="Open", callback=lambda s, t, d: print("Open File"))
            # create a save file menu item
            dcg.MenuItem(C, label="Save", callback=lambda s, t, d: print("Save File"))
            # create a separator
            dcg.Separator(C)
            # create an exit menu item
            dcg.MenuItem(C, label="Exit", callback=lambda s, t, d: C.viewport.close())

    dcg.Button(C, label="Open Style Editor", callback=lambda s, t, d: dcg.utils.StyleEditor(C))
    lock_axes_button = dcg.Button(C, label="lock axes", callback=lambda s, t, d: lock_axes(s, t, d))

    with dcg.HorizontalLayout(C):
        x_value=dcg.Text(C, value="Hello, World!")
        y_value=dcg.Text(C, value="Hello, World!")

    with dcg.Plot(C, label="Style Editor Demo", height='filly', width='fillx', has_box_select=True) as plot:  #,callback=mouse_click_callback) #it seems this callback is for when the value changes, not for mouse movement
        # Generate sample data
        x = np.linspace(0, 10, 100)

        Irregular_x_y = (
            (0,0),
            (1, 1),
            (4, 0),
            (8, 3),
            (12, 1),
            (16, 100))  # the last point in the array seems to terminate the plot
            # it seems to do this regardless of the y value, so maybe it is an x range issue
        
        # unzip the list of tuples into two lists
        x_irregular, y_irregular = zip(*Irregular_x_y)
            
        # Create multiple series
        dcg.PlotLine(C, label="Sine", X=x, Y=np.sin(x))
        dcg.PlotScatter(C, label="Cosine", X=x, Y=np.cos(x))
        dcg.PlotErrorBars(C, label="Error Bars", X=x, Y=np.sin(x),
                        negatives=np.random.uniform(0.1, 0.5, size=x.shape),
                        positives=np.random.uniform(0.1, 0.5, size=x.shape))
        dcg.PlotDigital(C, label="Digital", X=x, Y=np.random.randint(0, 2, size=x.shape))
        dcg.PlotDigital(C, label="Digital Irregular", X=x_irregular, Y=y_irregular)


    # This was recently updated in the demo
    with plot:
        dcg.PlotAnnotation(C, label="Annotation", x=x[100], y=np.sin(x[50]), text="Peak",bg_color=(0.9, 0.1, 0.1, 1.0))
        with plot.X1:
            dcg.AxisTag(C, coord=x[50], text="Peak",bg_color=(0.9, 0.1, 0.1, 1.0))

        with dcg.DrawInPlot(C):
            # Good: Pixel thickness (constant visual size)
            dcg.DrawStar(C, center=(2, 0.5), radius=1, num_points=6, 
                        color=(255, 255, 0), thickness=-2,
                        direction=0.3, inner_radius=0.5)
            w=2
            h=1
            ll=(4,0.25)
            button_rect = dcg.DrawRect(C, pmin=ll, pmax=(ll[0]+w, ll[1]+h), 
                            color=(200, 200, 0, 0), #(0, 255, 0), # trying to have no boarder
                            fill=(200, 200, 0, 150), 
                            thickness=0)
            
            # Create an invisible button at the same position
            invisible_btn = dcg.DrawInvisibleButton(C, p1=ll, p2=(ll[0]+w, ll[1]+h),
                                                  button=dcg.MouseButtonMask.ANY,
                                                  capture_mouse=True)#,show=False)

    # add the callback to the handler list in the plot object
    plot.handlers += [
        dcg.MouseMoveHandler(C, callback=mouse_callback),
        dcg.ClickedHandler(C, callback=clicked_callback)
    ]


loop.run_until_complete(run_viewport_loop(C.viewport))