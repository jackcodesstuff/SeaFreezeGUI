import json, sys, pandas, scipy.io, numpy as np, os
import seafreeze.seafreeze as sf, phaselines as phaselines
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplashScreen, QStyledItemDelegate, QWidget, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QCheckBox, QFileDialog, QSizePolicy, QHeaderView, QSpacerItem
)
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
)
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import matplotlib.lines as mlines
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime
 
class GraphWindow(QMainWindow):
    # Initializes the window, primary widget and layout
    # Establishes layouts and variables
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SeaFreeze Version 1.0.1")
        self.set_proportional_geometry(0.1, 0.1, 0.85, 0.8)
        # self.setStyleSheet("border-radius: 10px; border: 1px solid gray")

        # Central Widget and Layout
        self.central_widget = QWidget(self)
        self.central_widget.setStyleSheet("background-color: #f0f4f8")
        self.setCentralWidget(self.central_widget)
        layout = QHBoxLayout(self.central_widget)

        # Graph Tab Setup
        self.graph_tab = QWidget()
        self.graph_figure = plt.figure()
        self.graph_figure.set_facecolor('#f0f4f8')
        self.graph_ax = self.graph_figure.add_subplot(111, projection='3d')
        self.graph_ax.set_facecolor('#f0f4f8')
        self.graph_canvas = FigureCanvas(self.graph_figure)
        graph_box = QVBoxLayout()
        toolbar_layout = QHBoxLayout()
        toolbar = NavigationToolbar(self.graph_canvas, self)
        toolbar_layout.addWidget(toolbar, alignment=Qt.AlignmentFlag.AlignHCenter)
        spacer = QSpacerItem(0, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)  # 40px spacer
        graph_box.addItem(spacer)
        graph_box.addLayout(toolbar_layout)
        self.layout_graphtab = QVBoxLayout(self.graph_tab)
        self.layout_graphtab.addLayout(graph_box)
        self.layout_graphtab.addWidget(self.graph_canvas)

        # Water Phase (WP) Tab Setup
        self.WP_tab = QWidget()
        self.WP_figure = plt.figure(figsize=(5, 5))
        self.WP_figure.set_facecolor('#f0f4f8')
        self.WP_ax = self.WP_figure.add_subplot(111)
        self.WP_ax.set_facecolor('#f0f4f8')
        self.WP_ax.set_xlim(0, 2300)
        self.WP_ax.set_ylim(0, 375)
        self.WP_ax.set_xlabel("Pressure (MPa)")
        self.WP_ax.set_ylabel("Temperature (K)")
        self.WP_ax.set_title("Water Phase Diagram")
        self.cursor_marker, = self.WP_ax.plot([], [], marker='o', color='red', markersize=8, linestyle='None')
        self.WP_canvas = FigureCanvas(self.WP_figure)
        # self.WP_canvas.setMaximumSize(800, 600)
        self.WP_canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        self.layout_WP = QHBoxLayout(self.WP_tab)
        self.WP_plotting_checkboxes = {}
        self.triple_points_checkbox = QCheckBox("Triple-Point(s)")
        self.delta_h_s_checkbox = QCheckBox("DeltaH\nand DeltaS")
        self.delta_v_checkbox = QCheckBox("DeltaV")
        self.WP_txt_checkbox = QCheckBox(".txt")
        self.plot_complete_button = None
        self.plot_complete_button_clicked = False
        self.plot_curves_button_clicked = False
        # Load data from a MATLAB .mat file
        self.WP_data = scipy.io.loadmat('WPD.mat', variable_names=['Solid_Solid', 'Melt_Line'])

        self.checkedPhaselines = [("Ih/Liquid", 0),
                        ("Ih/II", 0),
                        ("Ih/III", 0),
                        ("II/III", 0),
                        ("II/V", 0),
                        ("II/VI", 0),
                        ("III/V", 0),
                        ("III/Liquid", 0),
                        ("V/Liquid", 0),
                        ("VI/Liquid", 0),
                        ("V/VI", 0)]
        # Triple Point circles
        self.circles_dict = {
            "Ih/Liquid": [(207.5930, 251.1191)],
            "Ih/II": [(209.885, 238.2371)],
            "Ih/III": [(209.885, 238.2377), (207.5930, 251.1191)],
            "II/III": [(355.5042, 249.4176), (209.885, 238.2379)],
            "II/V": [(670.8401, 201.9335), (355.5042, 249.4176)],
            "II/VI": [(670.8401, 201.9335)],
            "III/V": [(355.5042, 249.4176), (350.1095, 256.1641)],
            "III/Liquid": [(350.1095, 256.1641), (207.5930, 251.1191)],
            "V/Liquid": [(634.3997, 273.40653), (350.1095, 256.1641)],
            "VI/Liquid": [(634.399, 273.4063)],
            "V/VI": [(634.39, 273.4063), (670.8409, 201.9335)]
        }
        self.contours = {}
        self.phaseline_data = {}
        self.phaseline_D_S_H_data = {}
        self.total_points = []
        self.complete_diagram_points = []

        self.calculator_tab = QWidget()
        self.inputs_widget = QWidget()

        # Create the tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.show_inputs_section)
        layout.addWidget(self.tab_widget)
        self.tab_widget.addTab(self.graph_tab, "Graph")

        self.selected_graph_type = "Gibb's Energy" # graph type selected from dropdown
        self.graph_type_buttons = [] # list of graph type buttons
        self.graph_type_button_labels = [] # labels for graph types
        self.material = None # material for saving purposes
        self.ices = ['Ice Ih (0.1-400 MPa, 0.1-301 K)',
                    'Ice II (0.1-900 MPa, 0.1-270 K)', 'Ice III (0.1-500 MPa, 0.1-270 K)',
                    'Ice V (0.1-1000 MPa, 0.1-300 K)', 'Ice VI (0.1-3000 MPa, 0.1-400 K)']

        # Button styles
        self.current_button_mat = None
        self.jmol_kg_button_mat = None

        # J/mol/kg button logic
        self.jmol_clicked = True
        self.jkg_clicked = True
        self.jkg_clicked_last = True
        self.jmol_clicked_last = False
        self.file_name = ""
        # Dataframe for excel saving
        self.df = None
        # dictionary of file name to file data
        self.file_dict = {}

        # Dictionary that stores the data points associated with every
        # graph type so that given a material and inputs,
        # all types of data may be exported
        self.graphtype_out_dict = {}

        # Dictionary that stores points for an individual graph type
        self.graphtype_to_points = {}

        # list of checked boxes for graphtypes
        self.graphtype_export_checkboxes = []
        self.graphtype_index = 0
        self.cursor_annotation = None
        self.cursor_x = None
        self.cursor_y = None
        self.last_clicked_point = None

        # Checkboxes on Input side of Main Graph screen
        self.dataset_layout = None
        self.dataset_checkboxes = QGridLayout()
        self.export_as_checkboxes = QGridLayout()
        self.export_as_checkboxes_list = [] # list of .txt .xlsx .json checkboxes
        self.WPD_export_checkboxes = [] # list of checkboxes for WPD
        self.export_type = ""
        self.dataset_dropdown_space = 0
        self.selected_material = ""
        self.dropdown = QComboBox()
        self.data_dropdown = QComboBox()

        self.p_input_boxes = [QLineEdit() for _ in range(3)]
        self.t_input_boxes = [QLineEdit() for _ in range(3)]

        for p_input_box in self.p_input_boxes:
            p_input_box.setStyleSheet("border: 1px solid #ccc;" +
                                    "border-radius: 4px;" +
                                    "padding: 5px;" +
                                    "background: white;" +
                                    "selection-background-color: #4a90e2;" +
                                    "selection-color: white;")

        for t_input_box in self.t_input_boxes:
            t_input_box.setStyleSheet("border: 1px solid #ccc;" +
                                    "border-radius: 4px;" +
                                    "padding: 5px;" +
                                    "background: white;" +
                                    "selection-background-color: #4a90e2;" +
                                    "selection-color: white;")

        self.checkbox_data_map = {}
        self.file_paths = []

        self.prev_nP = 100
        self.prev_nT = 100
        self.prev_Tmin = 1
        self.prev_Tmax = 100
        self.prev_Pmin = 1
        self.prev_Pmax = 100

        self.prev_mat = None
        self.mat = None

        # Define a dictionary to map button labels to units
        self.units_mapping = {
            "Gibb's Energy": "J/kg", # J/kg<->J/mol
            "Entropy": "J/K/kg", # J/kg<->J/mol
            "Enthalpy": "J/kg", # J/kg<->J/mol
            "Internal Energy": "J/kg", # J/kg<->J/mol
            "Specific Heat (Cp)": "J/kg/K", # J/kg/K<->J/mol/K
            "Specific Heat (Cv)": "J/kg/K", # J/kg/K<->J/mol/K
            "Density": "kg/m³", # kg/m³<->kg/m³
            "Isothermal Bulk Modulus": "MPa", # MPa<->MPa
            "Isoentropic Bulk Modulus": "MPa", # MPa<->MPa
            "Thermal Expansivity": "K⁻¹", # K⁻¹<->K⁻¹
            "Bulk Modulus Derivative": "unitless", # unitless<->unitless
            "Sound Speed": "m/s", # m/s<->m/s
            "P Wave Velocity (solids)": "m/s",  # m/s (for solids only)
            "S Wave Velocity (solids)": "m/s",  # m/s (for solids only)
            "Shear Modulus (solids)": "MPa",  # MPa (for solids only)
        }
        self.units = "J/kg"

        self.init_single_point_calculator_tab()
        self.init_WP_Diagram_Tab()
        self.init_more_tab()
        self.init_inputs_section()

    # Sets window size
    def set_proportional_geometry(self, x_ratio, y_ratio, width_ratio, height_ratio):
        screen_geometry = QApplication.primaryScreen().geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        window_x = int(screen_width * x_ratio)
        window_y = int(screen_height * y_ratio)
        window_width = int(screen_width * width_ratio)
        window_height = int(screen_height * height_ratio)

        self.setGeometry(window_x, window_y, window_width, window_height)

    # Handle tab changes to show inputs sectinos
    def show_inputs_section(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab in [self.graph_tab, self.calculator_tab]:
            self.inputs_widget.show()
        else:
            self.inputs_widget.hide()

    def resize_graph_to_window(self):
        self.graph_canvas.hide()
        self.graph_canvas.resize(self.size())
        self.graph_figure.tight_layout()
        self.graph_canvas.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Ensure the graph resizes proportionally when the window is resized
        self.resize_graph_to_window()

    ## MAIN GRAPH

    # Updates the main graph
    def update_graph(self):
        if not self.mat:
            return

        self.title = '\n'.join(self.mat.split('\n')[:2]) + " " + self.selected_graph_type + (
            " (" + self.units + ")" if self.selected_graph_type else "Gibb's Energy")

        # Retrieve current input values
        self.current_nP = int(self.p_input_boxes[2].text()) if self.p_input_boxes[2].text() else 100
        self.current_nT = int(self.t_input_boxes[2].text()) if self.t_input_boxes[2].text() else 100
        self.current_Tmin = np.double(self.t_input_boxes[0].text()) if self.t_input_boxes[0].text() else 240
        self.current_Tmax = np.double(self.t_input_boxes[1].text()) if self.t_input_boxes[1].text() else 270
        self.current_Pmin = np.double(self.p_input_boxes[0].text()) if self.p_input_boxes[0].text() else 0.1
        self.current_Pmax = np.double(self.p_input_boxes[1].text()) if self.p_input_boxes[1].text() else 400
       
        # If values haven't been changed
        if (self.current_nP, self.current_nT, self.current_Tmin, self.current_Tmax, self.current_Pmin, self.current_Pmax) == (
            self.prev_nP, self.prev_nT, self.prev_Tmin, self.prev_Tmax, self.prev_Pmin, self.prev_Pmax):
            self.typed_inputs_no_change = True
            # And if material hasn't been changed
            if self.mat == self.prev_mat:
                return
        else:
            self.typed_inputs_no_change = False
       
        # Update previous values with current values
        self.prev_nP = self.current_nP if self.current_nP else None
        self.prev_nT = self.current_nT if self.current_nT else None
        self.prev_Tmin = self.current_Tmin if self.current_Tmin else None
        self.prev_Tmax = self.current_Tmax if self.current_Tmax else None
        self.prev_Pmin = self.current_Pmin if self.current_Pmin else None
        self.prev_Pmax = self.current_Pmax if self.current_Pmax else None

        none_p = self.current_Pmin == None or self.current_Pmax == None or self.current_nP == None
        none_t = self.current_Tmin == None or self.current_Tmax == None or self.current_nT == None
        invalid_currents = none_p or none_t

        self.ok_to_graph = True
        # Displays error message on incomplete or invalid input
        match self.mat:
            case 'Liquid water\n(Bollengier et al. 2019)\n(0.1-2300 MPa, 239-501 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 2300 and 239 <= self.current_Tmin
                              <= self.current_Tmax <= 501)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Liquid water\n(IAPWS 95)\n(0.1-299.5 GPa, 180-19,993 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 299500
                                and 180 <= self.current_Tmin <= self.current_Tmax <= 19993)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Liquid water\n(Abrahamson et al. 2004)\n(0.1-100 GPa, 240-10,000 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 100000
                                and 240 <= self.current_Tmin <= self.current_Tmax <= 10000)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Ice Ih (0.1-400 MPa, 0.1-301 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 400
                                and 0.1 <= self.current_Tmin <= self.current_Tmax <= 301)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Ice II (0.1-900 MPa, 0.1-270 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 900
                                and 0.1 <= self.current_Tmin <= self.current_Tmax <= 270)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Ice III (0.1-500 MPa, 0.1-270 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 500
                                and 0.1 <= self.current_Tmin <= self.current_Tmax <= 270)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Ice V (0.1-1000 MPa, 0.1-300 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 1000
                                and 0.1 <= self.current_Tmin <= self.current_Tmax <= 301)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
            case 'Ice VI (0.1-3000 MPa, 0.1-400 K)':
                valid_nums = (0.1 <= self.current_Pmin <= self.current_Pmax <= 3000
                                and 0.1 <= self.current_Tmin <= self.current_Tmax <= 400)
                if not valid_nums or invalid_currents:
                    self.error()
                    return
                else:
                    self.ok_to_graph = True
 
        # Define the PT conditions
        if (self.current_Pmin and self.current_Pmax and self.current_nP) and (self.current_Tmin and self.current_Tmax and self.current_nT):
            P = np.arange(self.current_Pmin, self.current_Pmax, (self.current_Pmax-self.current_Pmin)/self.current_nP)
            T = np.arange(self.current_Tmin, self.current_Tmax, (self.current_Tmax-self.current_Tmin)/self.current_nT)
            if self.current_nP == 1:
                P = np.array([self.current_Pmin], dtype='float64')
            else:
                P = np.arange(self.current_Pmin, self.current_Pmax,
                            (self.current_Pmax - self.current_Pmin) / self.current_nP)
            if self.current_nT == 1:
                T = np.array([self.current_Tmin], dtype='float64')
            else:
                T = np.arange(self.current_Tmin, self.current_Tmax,
                            (self.current_Tmax - self.current_Tmin) / self.current_nT)
            P = P.flatten()
            T = T.flatten()
            PT = np.array([P, T], dtype='object')

        if (self.current_nP < 1 or self.current_nT < 1):
            self.error()
            return

        out = None
        if self.mat == None:
            return
        else:
            if self.ok_to_graph:
                if self.mat == 'Liquid water\n(Bollengier et al. 2019)\n(0.1-2300 MPa, 239-501 K)':
                    out = sf.getProp(PT, 'water1')
                elif self.mat == 'Liquid water\n(Abrahamson et al. 2004)\n(0.1-100 GPa, 240-10,000 K)':
                    out = sf.getProp(PT, 'water2')
                elif self.mat == 'Liquid water\n(IAPWS 95)\n(0.1-299.5 GPa, 180-19,993 K)':
                    out = sf.getProp(PT, 'water_IAPWS95')
                elif self.mat == 'Ice Ih (0.1-400 MPa, 0.1-301 K)':
                    out = sf.getProp(PT, 'Ih')
                elif self.mat == 'Ice II (0.1-900 MPa, 0.1-270 K)':
                    out = sf.getProp(PT, 'II')
                elif self.mat == 'Ice III (0.1-500 MPa, 0.1-270 K)':
                    out = sf.getProp(PT, 'III')
                elif self.mat == 'Ice V (0.1-1000 MPa, 0.1-300 K)':
                    out = sf.getProp(PT, 'V')
                elif self.mat == 'Ice VI (0.1-3000 MPa, 0.1-400 K)':
                    out = sf.getProp(PT, 'VI')

        if self.mat in self.ices:
            match(self.selected_graph_type):
                case "Gibb's Energy":
                    A = np.transpose(np.array(out.G))
                case "Entropy":
                    A = np.transpose(np.array(out.S))
                case "Internal Energy":
                    A = np.transpose(np.array(out.U))
                case "Enthalpy":
                    A = np.transpose(np.array(out.H))
                case "Helmholtz free energy":
                    A = np.transpose(np.array(out.A))
                case "Density":
                    A = np.transpose(np.array(out.rho))
                case "Specific Heat (Cp)":
                    A = np.transpose(np.array(out.Cp))
                case "Specific Heat (Cv)":
                    A = np.transpose(np.array(out.Cv))
                case "Isothermal Bulk Modulus":
                    A = np.transpose(np.array(out.Kt))
                case "Isoentropic Bulk Modulus":
                    A = np.transpose(np.array(out.Ks))
                case "Bulk Modulus Derivative":
                    A = np.transpose(np.array(out.Kp))
                case "Thermal Expansivity":
                    A = np.transpose(np.array(out.alpha))
                case "Sound Speed":
                    A = np.transpose(np.array(out.vel))
                case "P Wave Velocity (solids)":
                    A = np.transpose(np.array(out.Vp))
                case "S Wave Velocity (solids)":
                    A = np.transpose(np.array(out.Vs))
                case "Shear Modulus (solids)":
                    A = np.transpose(np.array(out.shear))
                case _:
                    return
        elif self.mat not in self.ices and self.prev_mat not in self.ices:
            # Set A values according to graph type
            match(self.selected_graph_type):
                case "Gibb's Energy":
                    A = np.transpose(np.array(out.G))
                case "Entropy":
                    A = np.transpose(np.array(out.S))
                case "Internal Energy":
                    A = np.transpose(np.array(out.U))
                case "Enthalpy":
                    A = np.transpose(np.array(out.H))
                case "Helmholtz free energy":
                    A = np.transpose(np.array(out.A))
                case "Density":
                    A = np.transpose(np.array(out.rho))
                case "Specific Heat (Cp)":
                    A = np.transpose(np.array(out.Cp))
                case "Specific Heat (Cv)":
                    A = np.transpose(np.array(out.Cv))
                case "Isothermal Bulk Modulus":
                    A = np.transpose(np.array(out.Kt))
                case "Isoentropic Bulk Modulus":
                    A = np.transpose(np.array(out.Ks))
                case "Bulk Modulus Derivative":
                    A = np.transpose(np.array(out.Kp))
                case "Thermal Expansivity":
                    A = np.transpose(np.array(out.alpha))
                case "Sound Speed":
                    A = np.transpose(np.array(out.vel))
                case _:
                    return
        
        # in cases of saving with checkboxes
        # Dict to iterate through all possible graphs and store
        self.graphtype_out_dict = {
            "Gibb's Energy": np.transpose(np.array(out.G)),
            "Entropy": np.transpose(np.array(out.S)),
            "Enthalpy": np.transpose(np.array(out.H)),
            "Internal Energy": np.transpose(np.array(out.U)),
            "Helmholtz free energy": np.transpose(np.array(out.A)),
            "Density": np.transpose(np.array(out.rho)),
            "Specific Heat (Cp)": np.transpose(np.array(out.Cp)),
            "Specific Heat (Cv)": np.transpose(np.array(out.Cv)),
            "Isothermal Bulk Modulus": np.transpose(np.array(out.Kt)),
            "Isoentropic Bulk Modulus": np.transpose(np.array(out.Ks)),
            "Isothermal Bulk Modulus Derivative": np.transpose(np.array(out.Kp)),
            "Thermal Expansivity": np.transpose(np.array(out.alpha)),
            "Sound Speed": np.transpose(np.array(out.vel)),
        }

        if self.mat in self.ices:
            self.graphtype_out_dict.update({"Shear Modulus (solids)": np.transpose(np.array(out.shear))})
            self.graphtype_out_dict.update({"P Wave Velocity (solids)": np.transpose(np.array(out.Vp))})
            self.graphtype_out_dict.update({"S Wave Velocity (solids)": np.transpose(np.array(out.Vs))})

        if self.can_convert():
            # adjust for jmol/jkg conversion
            A = self.convert_to_jmol(A)

        self.resize_graph_to_window()

        if self.current_nP == 1 or self.current_nT == 1:
            # Replace the existing axis (if it's 3D)
            if isinstance(self.graph_ax, Axes3D):
                self.graph_ax.remove()
                self.graph_ax = self.graph_figure.add_subplot(111)
                self.graph_ax.clear()
            elif isinstance(self.graph_ax, Axes):
                self.graph_ax.clear()
            self.graph_figure.set_size_inches(6, 6)
            self.graph_figure.subplots_adjust(left=0.25, right=.9, bottom=0.15, top=0.8)
            if self.current_nP == 1:
                self.graph_ax.plot(T, A)
                self.graph_ax.set_xlabel('Temperature (K)', fontsize=10, labelpad=10)
                self.graph_ax.set_ylabel(self.mat, fontsize=10, labelpad=10)
                self.set_data([], T)
            elif self.current_nT == 1:
                self.graph_ax.plot(P, A.T)
                self.graph_ax.set_xlabel('Pressure (MPa)', fontsize=10, labelpad=10)
                self.graph_ax.set_ylabel(self.mat, fontsize=10, labelpad=10)
                self.set_data(P, [])
            else:
                return

            self.graph_figure.set_facecolor('#f0f4f8')
            self.graph_ax.set_facecolor('#f0f4f8')
            self.graph_ax.set_title(self.title)
            self.graph_canvas.draw()
        else:
            # Replace the existing axis (if it's 2D)
            if isinstance(self.graph_ax, Axes):
                self.graph_ax.remove()
                self.graph_ax = self.graph_figure.add_subplot(111, projection='3d')
                self.graph_ax.clear()
            elif isinstance(self.graph_ax, Axes3D):
                self.graph_ax.clear()

            P_grid, T_grid = np.meshgrid(P, T)
            self.graph_figure.set_size_inches(7, 7)
            self.graph_figure.subplots_adjust(left=0.1, right=.8, bottom=0, top=1)
            self.graph_figure.set_facecolor('#f0f4f8')
            self.graph_ax.view_init(elev=20, azim=-110) # maybe 15, -130
            self.graph_ax.set_facecolor('#f0f4f8')
            self.graph_ax.plot_surface(P_grid, T_grid, A, cmap='viridis')
            self.graph_ax.set_xlabel('Pressure (MPa)', labelpad=10)
            self.graph_ax.set_ylabel('Temperature (K)', labelpad=10)
            self.graph_ax.set_zlabel(self.selected_graph_type, labelpad=10)
            self.graph_ax.set_title(self.title, y=1, fontsize = 12)
            self.resize_graph_to_window()
            self.graph_canvas.draw()
            self.set_data(P, T)

    # Clears graph
    def clear_graph(self, axis):
        axis.clear()

    # Parses imported file for graphtype, material and data points
    # returns a tuple with each
    def parse_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                if file_path.endswith(".txt"):
                    lines = file.readlines()
                    # Extract header information
                    graph_type_mat = lines[0].split()
                    graph_type_mat = [element.replace('\n', '') for element in graph_type_mat]

                    # Find the start of data points (skip the header section)
                    data_start_index = 0
                    for i, line in enumerate(lines):
                        if '##############################################################' in line:
                            data_start_index = i + 1
                            break
                    # Extract data points
                    data_points = []
                    for line in lines[data_start_index:]:
                        point = tuple(map(float, line.strip().split(',')))
                        data_points.append(point)
                    nT = False
                    nP = False
                    if "1" in lines[3].split():
                        nT = True
                    if "1" in lines[4].split():
                        nP = True
                    return graph_type_mat, data_points, nT, nP
                else:
                    data = json.load(file)
                    header = data[0] if len(data) > 0 else ""
                    graph_type_mat = header.split()
                    data_points_start_index = data.index(
                        '##############################################################') + 1
                    data_points = []
                    points = data[data_points_start_index:]
                    # Now you can iterate over the data points
                    for point in points:
                        # Assuming each point is stored as a list of values in the JSON
                        data_points.append(tuple(map(float, point.split(','))))
                    nT = False
                    nP = False
                    if "1" in data[3].split():
                        nT = True
                    if "1" in data[4].split():
                        nP = True
                    return graph_type_mat, data_points, nT, nP
        except FileNotFoundError:
            return None

    # Generates main graph from imported data
    def import_graph(self):
        file_url, _ = QFileDialog.getOpenFileUrl(self, "Select File", QUrl(), "All Files (*.*)")
        # Convert QUrl to a local file path
        file_path = file_url.toLocalFile()
        try:
            graph_type_mat, data_points, nT, nP = self.parse_file(file_path)
            self.graph_ax.clear()
            if graph_type_mat and (pt for pt in data_points):
                # Define possible cases
                waters = ['water 1', 'water 2', 'water 3']
                ices = ['Ice Ih', 'Ice II', 'Ice III', 'Ice V', 'Ice VI']

                # Check if any of the cases is a substring of the input
                matched_case = ''
                graph_type = ''
                state = ''
                for case in waters + ices:
                    case_parts = case.split()
                    len_sub = len(case_parts)
                    
                    # Get the last `len_sub` elements from `graph_type_mat`
                    last_elements = graph_type_mat[-len_sub:]
                    
                    # Check if `case_parts` matches `last_elements`
                    if last_elements == case_parts:
                        matched_case = case_parts                    
                        # Remove matched case from graph_type_mat
                        for part in matched_case:
                            if part in graph_type_mat:
                                graph_type_mat.remove(part)
                        graph_type = ' '.join(graph_type_mat).strip()

                        if "Liquid" in graph_type:
                            graph_type, state = graph_type.split("Liquid", 1)
                            state = "Liquid"
                        elif "Ice" in graph_type:
                            graph_type, state = graph_type.split("Ice", 1)
                            state = "Ice"
                        break
                mat = ' '.join(matched_case).strip()
                data_array = np.array(data_points)
                three_d = False
                two_d = False
                for item in data_array[:1]:
                    if len(item) == 3:
                        three_d = True
                        break
                    elif len(item) == 2:
                        two_d = True
                        break
                if three_d:
                    P = data_array[::80, 0]  # All x values
                    T = data_array[::80, 1]  # All y values
                    PT = np.array([P, T], dtype='float64')
                    P_grid, T_grid = np.meshgrid(P, T)

                    out = None
                    match mat:
                        case 'Ice Ih':
                            out = sf.getProp(PT, 'Ih')
                        case 'Ice II':
                            out = sf.getProp(PT, 'II')
                        case 'Ice III':
                            out = sf.getProp(PT, 'III')
                        case 'Ice V':
                            out = sf.getProp(PT, 'V')
                        case 'Ice VI':
                            out = sf.getProp(PT, 'VI')
                        case 'water 1':
                            out = sf.getProp(PT, 'water1')
                        case 'water 3':
                            out = sf.getProp(PT, 'water_IAPWS95')
                        case 'water 2':
                            out = sf.getProp(PT, 'water2')
                    
                    if state == "Ice":
                        match(graph_type.strip()):
                            case "Gibb's Energy":
                                A = np.transpose(np.array(out.G))
                            case "Entropy":
                                A = np.transpose(np.array(out.S))
                            case "Internal Energy":
                                A = np.transpose(np.array(out.U))
                            case "Enthalpy":
                                A = np.transpose(np.array(out.H))
                            case "Helmholtz free energy":
                                A = np.transpose(np.array(out.A))
                            case "Density":
                                A = np.transpose(np.array(out.rho))
                            case "Specific Heat (Cp)":
                                A = np.transpose(np.array(out.Cp))
                            case "Specific Heat (Cv)":
                                A = np.transpose(np.array(out.Cv))
                            case "Isothermal Bulk Modulus":
                                A = np.transpose(np.array(out.Kt))
                            case "Isoentropic Bulk Modulus":
                                A = np.transpose(np.array(out.Ks))
                            case "Isothermal Bulk Modulus Derivative":
                                A = np.transpose(np.array(out.Kp))
                            case "Thermal Expansivity":
                                A = np.transpose(np.array(out.alpha))
                            case "Sound Speed":
                                A = np.transpose(np.array(out.vel))
                            case "P Wave Velocity (solids)":
                                A = np.transpose(np.array(out.Vp))
                            case "S Wave Velocity (solids)":
                                A = np.transpose(np.array(out.Vs))
                            case "Shear Modulus (solids)":
                                A = np.transpose(np.array(out.shear))
                            case _:
                                return
                    else:
                        match(graph_type.strip()):
                            case "Gibb's Energy":
                                A = np.transpose(np.array(out.G))
                            case "Entropy":
                                A = np.transpose(np.array(out.S))
                            case "Internal Energy":
                                A = np.transpose(np.array(out.U))
                            case "Enthalpy":
                                A = np.transpose(np.array(out.H))
                            case "Helmholtz free energy":
                                A = np.transpose(np.array(out.A))
                            case "Density":
                                A = np.transpose(np.array(out.rho))
                            case "Specific Heat (Cp)":
                                A = np.transpose(np.array(out.Cp))
                            case "Specific Heat (Cv)":
                                A = np.transpose(np.array(out.Cv))
                            case "Isothermal Bulk Modulus":
                                A = np.transpose(np.array(out.Kt))
                            case "Isoentropic Bulk Modulus":
                                A = np.transpose(np.array(out.Ks))
                            case "Isothermal Bulk Modulus Derivative":
                                A = np.transpose(np.array(out.Kp))
                            case "Thermal Expansivity":
                                A = np.transpose(np.array(out.alpha))
                            case "Sound Speed":
                                A = np.transpose(np.array(out.vel))
                            case _:
                                return

                    if mat == 'water 1':
                        mat = 'Liquid water\n(Bollengier et al. 2019)'
                    elif mat == 'water 2':
                        mat = 'Liquid water\n(Abrahamson et al. 2004)'
                    elif mat == 'water 3':
                        mat = 'Liquid water\n(IAPWS 95)'

                    title = mat + " " + graph_type
                    if isinstance(self.graph_ax, Axes):
                        self.graph_ax.remove()
                        self.graph_ax = self.graph_figure.add_subplot(111, projection = '3d')
                        self.graph_ax.clear()
                    self.graph_ax.plot_surface(P_grid, T_grid, A, cmap='viridis')
                    self.graph_ax.set_xlabel('Pressure (MPa)', labelpad=10)
                    self.graph_ax.set_ylabel('Temperature (K)', labelpad=10)
                    self.graph_ax.set_zlabel(graph_type + " (" + "units" + ")", labelpad=10)
                    self.graph_ax.set_title(title, y=1, fontsize = 12)
                    self.graph_ax.view_init(elev=20, azim=-110)
                    self.graph_ax.set_facecolor('#f0f4f8')
                    self.graph_canvas.draw()
                if two_d:
                    X = data_array[:, 0]  # All x values
                    A = data_array[:, 1]  # All A values (Y for 2d graph)
                    x_label = ''
                    # nT is 1, so plot P and A
                    if nT:
                        x_label = 'Pressure (MPa)'
                    # nP is 1, so plot T and A
                    elif nP:
                        x_label = 'Temperature (K)'
                    
                    title = mat + " " + graph_type
                    if isinstance(self.graph_ax, Axes3D):
                        self.graph_ax.remove()
                        self.graph_ax = self.graph_figure.add_subplot(111)
                        self.graph_ax.clear()
                    self.graph_ax.plot(X, A)
                    self.graph_ax.set_xlabel(x_label, fontsize=10, labelpad=10)
                    self.graph_ax.set_ylabel(self.mat, fontsize=10, labelpad=10)
                    self.graph_ax.set_title(title, y=1, fontsize = 12)
                    self.graph_ax.set_facecolor('#f0f4f8')
                    self.graph_canvas.draw()
        except TypeError:
            print("Invalid File")

    # Displays error message
    def error(self):
        invalid_n = self.current_nP < 1 or self.current_nT < 1
        error_messages = {
            'Liquid water\n(Bollengier et al. 2019)\n(0.1-2300 MPa, 239-501 K)': "Error: must have 0.1-2300 MPa, 239-501 K",
            'Liquid water\n(IAPWS 95)\n(0.1-299.5 GPa, 180-19,993 K)': "Error: must have 0.1-299.5 GPa, 180-19,993 K",
            'Liquid water\n(Abrahamson et al. 2004)\n(0.1-100 GPa, 240-10,000 K)': "Error: must have 0.1-100 GPa, 240-10,000 K",
            'Ice Ih (0.1-400 MPa, 0.1-301 K)': "Error: must have 0.1-400 MPa, 0.1-301 K",
            'Ice II (0.1-900 MPa, 0.1-270 K)': "Error: must have 0.1-900 MPa, 0.1-270 K",
            'Ice III (0.1-500 MPa, 0.1-270 K)': "Error: must have 0.1-500 MPa, 0.1-270 K",
            'Ice V (0.1-1000 MPa, 0.1-300 K)': "Error: must have 0.1-1000 MPa, 0.1-300 K",
            'Ice VI (0.1-3000 MPa, 0.1-400 K)': "Error: must have 0.1-3000 MPa, 0.1-400 K",
        }
        msg = None
        if invalid_n and self.current_nP is not None and self.current_nT is not None :
            if self.current_nP < 1:
                msg = "Error: nP must be at least 1"
            else:
                msg = "Error: nT must be at least 1"
        else:
            for key, value in error_messages.items():
                if self.mat == key:
                    msg = value
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(msg)

        # Close the error message after 3 seconds
        timer = QTimer()
        timer.timeout.connect(msg_box.close)
        timer.start(3000)  # 3000 milliseconds (3 seconds)
        msg_box.exec()

    # Checks if conversion can take
    # place to j/mol from j/kg
    def can_convert(self):
        if self.selected_graph_type == "Gibb's Energy" or (self.selected_graph_type == "Entropy"
                or self.selected_graph_type == "Enthalpy") or (self.selected_graph_type == "Internal Energy"
                or self.selected_graph_type == "Specific Heat (Cp)") or self.selected_graph_type == "Specific Heat (Cv)":
            return True

    # Converts data to j/mol from j/kg
    def convert_to_jmol(self, A):
        A = np.array(A)
        if self.jmol_clicked and self.jkg_clicked_last:
            A /= 55.5084351
        return A

    # Handles logic for jules button clicks
    def on_jules_buttons_click(self, button):
        # Check if there's a previously clicked button and make it normal
        if self.jmol_kg_button_mat is not None:
            self.make_jules_button_normal(self.jmol_kg_button_mat)

        if button == self.Jkg_button:
            self.jkg_clicked = True
            self.jmol_clicked = False
            self.jmol_clicked_last = True
        else:
            self.jmol_clicked = True
            self.jkg_clicked = False
            self.jkg_clicked_last = True

        # Make the clicked button gray
        self.make_jules_button_gray(button, "#A9A9A9")
        self.jmol_kg_button_mat = button
        self.update_graph()
   
    # Sets the data for exporting
    def set_data(self, P, T):
        data = None
        if self.current_nT and self.current_nP:
            # Loop through all data outputs so that
            # every type of data can be exported
            # for the selected material and inputs
            for graphtype, A in self.graphtype_out_dict.items():
                if A is not None:
                    if len(P) == 0:
                        data = list(zip(T, A.ravel()))
                    elif len(T) == 0:
                        data = list(zip(P, A.ravel()))
                    else:
                        data = list(zip(P.ravel(), T.ravel(), A.ravel()))
                    self.graphtype_to_points.update({graphtype: data})

    ## INPUTS SECTION

    # Initializes right-side input section
    def init_inputs_section(self):
        inputs_layout = QVBoxLayout(self.inputs_widget)        

        ## SELECT MATERIAL DROPDOWN
        dropdown_layout = QHBoxLayout()
        dropdown_layout.addSpacing(-80)
        dropdown_label = QLabel("    Select Material Here:")
        dropdown_label.setFixedWidth(190)
        select_material_font = dropdown_label.font()
        select_material_font.setPointSize(12)
        select_material_font.setFamily("Arial")
        dropdown_label.setFont(select_material_font)
        dropdown_layout.addWidget(dropdown_label)
       
        # Create and add the dropdown to the layout
        self.dropdown = QComboBox()
        self.dropdown.addItems(['', 'Liquid water\n(Bollengier et al. 2019)\n(0.1-2300 MPa, 239-501 K)',
                                'Liquid water\n(IAPWS 95)\n(0.1-299.5 GPa, 180-19,993 K)',
                                'Liquid water\n(Abrahamson et al. 2004)\n(0.1-100 GPa, 240-10,000 K)',
                                'Ice Ih (0.1-400 MPa, 0.1-301 K)', 'Ice II (0.1-900 MPa, 0.1-270 K)',
                                'Ice III (0.1-500 MPa, 0.1-270 K)', 'Ice V (0.1-1000 MPa, 0.1-300 K)',
                                'Ice VI (0.1-3000 MPa, 0.1-400 K)'])
        self.dropdown.currentIndexChanged.connect(
            lambda index: (self.update_dropdown(index))
        )
        self.dropdown.currentIndexChanged.connect(self.update_mat)
        self.dropdown.setFixedWidth(175)
        self.dropdown.setFixedHeight(50)
        self.dropdown.setStyleSheet("""
            QComboBox, QComboBox QAbstractItemView {
                border-radius: 5px;
                border: 1px solid #A9A9A9;
            }
            QComboBox::drop-down {
                width: 0px;            
            }
        """)
        dropdown_layout.addSpacing(-150)
        dropdown_layout.addWidget(self.dropdown)
        delegate = self.CenteredItemDelegate(self.dropdown)
        self.dropdown.setItemDelegate(delegate)

        ### BUTTONS SECTION
        self.graph_type_button_layout = QGridLayout() # graph type buttons
        self.graph_type_button_labels = ["Gibb's Energy", "Entropy", "Enthalpy", "Internal Energy", "Specific Heat (Cp)",
                         "Specific Heat (Cv)", "Density", "Isothermal Bulk Modulus",
                         "Isoentropic Bulk Modulus", "Bulk Modulus Derivative", "Thermal Expansivity", "Sound Speed",
                         "Shear Modulus (solids)", "P Wave Velocity (solids)", "S Wave Velocity (solids)"]
       
        buttons_per_column_ = 4

        # ADD DATA TYPE BUTTONS TO BUTTON LAYOUT
        for i, label in enumerate(self.graph_type_button_labels):
            row = i % buttons_per_column_
            col = i // buttons_per_column_

            button = QPushButton(label)
            self.graph_type_buttons.append(button)
            button.setFixedWidth(150)
            button.setMinimumHeight(30)
            button.setStyleSheet("border-radius: 5px; border: 1px solid #A9A9A9")
            self.graph_type_button_layout.addWidget(button, row, col)
            button.clicked.connect(lambda _, button=button, label=label: (self.on_button_click(button), self.get_material(label)))
            button.clicked.connect(self.update_graph)
       
        ## Choose Max / Mins Label
        choose_max_mins_layout = QHBoxLayout()
        max_min_label = QLabel("Choose Number of Points and Max/Mins:")
        max_min_label.setFixedSize(230, 25)
        max_min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        choose_max_mins_layout.addWidget(max_min_label)
       
        p_input_layout = QVBoxLayout()
        p_input_layout.addSpacing(-150)
        p_input_labels = ["Pmin:", "Pmax:", "nP:"]
        p_unit_labels = ["MPa", "MPa", ""]
        p_placeholder_texts = ["0.1", "400", "100"]

        # Add pressure input boxes to pressure layout
        for p_label, p_input_box, p_unit_label, p_placeholder_text in zip(p_input_labels, self.p_input_boxes, p_unit_labels, p_placeholder_texts):
            hbox = QHBoxLayout()
            hbox.setSpacing(50)
            hbox.setContentsMargins(10, 0, 10, 0)

            # Label for the parameter
            p_label_widget = QLabel(p_label)
            p_label_widget.setFixedSize(50, 50)
            p_label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hbox.addWidget(p_label_widget)

            # Input box for the parameter
            p_input_box.setMaximumWidth(45)
            p_input_box.setPlaceholderText(p_placeholder_text)
            p_input_box.setStyleSheet("""
                border: 1px solid #D3D3D3; 
                border-radius: 5px; 
                background: white; 
                padding: 5px;
                color: #000000;  /* Regular text color */
                QLineEdit {
                    border: 1px solid #D3D3D3;
                    border-radius: 5px;
                    background: white;
                    padding: 5px;
                    color: #000000;  /* Regular text color */
                }
                QLineEdit::placeholder {
                    color: #A9A9A9;  /* Placeholder text color */
                }
            """)
            
            hbox.addSpacing(-40)
            hbox.addWidget(p_input_box)
            hbox.addSpacing(-45)

            # Label for the unit
            p_unit_label_widget = QLabel(p_unit_label)
            p_unit_label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            p_unit_label_widget.setFixedSize(40, 40)
            hbox.addWidget(p_unit_label_widget)

            p_input_layout.addLayout(hbox)
 
        t_input_layout = QVBoxLayout()
        t_input_layout.addSpacing(-150)
        t_input_labels = ["Tmin:", "Tmax:", "nT:"]
        t_unit_labels = ["K", "K", ""]
        t_placeholder_texts = ["240", "270", "100"]

        # Add pressure input boxes to pressure layout
        for t_label, t_input_box, t_unit_label, t_placeholder_text in zip(t_input_labels, self.t_input_boxes, t_unit_labels, t_placeholder_texts):
            hbox = QHBoxLayout()
            hbox.setSpacing(50)
            hbox.setContentsMargins(10, 0, 10, 0)

            # Label for the parameter
            t_label_widget = QLabel(t_label)
            t_label_widget.setFixedSize(50, 50)
            t_label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hbox.addWidget(t_label_widget)

            # Input box for the parameter
            t_input_box.setMaximumWidth(45)
            t_input_box.setPlaceholderText(t_placeholder_text)
            t_input_box.setStyleSheet("""
                border: 1px solid #D3D3D3; 
                border-radius: 5px; 
                background: white; 
                padding: 5px;
                color: #000000;  /* Regular text color */
                QLineEdit {
                    border: 1px solid #D3D3D3;
                    border-radius: 5px;
                    background: white;
                    padding: 5px;
                    color: #000000;  /* Regular text color */
                }
                QLineEdit::placeholder {
                    color: #A9A9A9;  /* Placeholder text color */
                }
            """)
            
            hbox.addSpacing(-40)
            hbox.addWidget(t_input_box)
            hbox.addSpacing(-45)

            # Label for the unit
            t_unit_label_widget = QLabel(t_unit_label)
            t_unit_label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_unit_label_widget.setFixedSize(40, 40)
            hbox.addWidget(t_unit_label_widget)

            t_input_layout.addLayout(hbox)

        # Data Checkboxes Layout
        self.select_graphtype_export_data_layout = QVBoxLayout()
        self.data_type_label = QLabel("Select Data Type(s) To Export:")
        self.data_type_label.setFixedSize(230, 25)
        self.data_type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data_type_font = self.data_type_label.font()
        data_type_font.setPointSize(10)
        data_type_font.setFamily("Arial")
        self.data_type_label.setFont(data_type_font)
       
        self.graphtype_export_checkbox_labels = ["Specific Heat (Cp)", "Specific Heat (Cv)", "Density", "Thermal Expansivity", "Gibb's Energy",
                                    "Enthalpy", "Entropy", "Internal Energy", "Isothermal Bulk Modulus", "Isothermal Bulk Modulus Derivative",
                                    "Sound Speed", "P Wave Velocity (solids)", "S Wave Velocity (solids)", "Shear Modulus (solids)"]

        self.clear_layout(self.select_graphtype_export_data_layout)
       
        # Create Export Data Checkboxes
        buttons_per_column = 5
        for i, label in enumerate(self.graphtype_export_checkbox_labels):
            row = i % buttons_per_column
            col = i // buttons_per_column
            checkbox = QCheckBox(label)
            checkbox.setStyleSheet("""
            QCheckBox::indicator:unchecked {
                border: 1px solid #D3D3D3;
                background: white;
                border-radius: 5px;
                width: 15px;
                height: 15px;
            }
            """)
            self.dataset_checkboxes.addWidget(checkbox, row, col)
            checkbox.stateChanged.connect(self.graphtype_checkbox_state_changed)
       
        # J/kg Button
        self.Jkg_button = QPushButton("J/kg")
        self.Jkg_button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        self.Jkg_button.setFixedWidth(80)
        self.Jkg_button.setMaximumHeight(30)
        self.Jkg_button.clicked.connect(lambda: self.on_jules_buttons_click(self.Jkg_button))
        self.make_jules_button_gray(self.Jkg_button, "#A9A9A9")
        # J/mol Button
        self.Jmol_button = QPushButton("J/mol")
        self.Jmol_button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        self.Jmol_button.setFixedWidth(80)
        self.Jmol_button.setMaximumHeight(30)
        self.Jmol_button.clicked.connect(lambda: self.on_jules_buttons_click(self.Jmol_button))
       
        horizBox = QHBoxLayout()
        horizBox.addSpacing(-20)
        horizBox.addWidget(self.Jkg_button)
        horizBox.addSpacing(-100)
        horizBox.addWidget(self.Jmol_button)
       
        select_data_type_to_export_label_box = QHBoxLayout()
        select_data_type_to_export_label_box.addWidget(self.data_type_label)
        self.select_graphtype_export_data_layout.addLayout(select_data_type_to_export_label_box)
        self.select_graphtype_export_data_layout.addSpacing(10)
        self.select_graphtype_export_data_layout.addLayout(self.dataset_checkboxes)

        ## 'Export As' Section

        # Layout for Export As Checkboxes
        self.export_type_layout = QVBoxLayout()
        self.file_type_label = QLabel("Export As:")
        self.file_type_label.setFixedSize(230, 25)
        self.file_type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_type_font = self.file_type_label.font()
        file_type_font.setPointSize(10)
        file_type_font.setFamily("Arial")
        self.file_type_label.setFont(file_type_font)
       
        self.export_labels = [".xlsx", ".txt", ".json"]

        self.clear_layout(self.export_type_layout)
        self.export_as_checkboxes.setAlignment(Qt.AlignmentFlag.AlignHCenter)
       
        # Creating Export As Checkboxes
        for i, label in enumerate(self.export_labels):
            r = 1
            c = i
            checkbox = QCheckBox(label)
            checkbox.setStyleSheet("""
            QCheckBox::indicator:unchecked {
                border: 1px solid #D3D3D3;
                background: white;
                border-radius: 5px;
                width: 15px;
                height: 15px;
            }
            """)
            checkbox.stateChanged.connect(self.export_as_checkbox_state_changed)
            self.export_as_checkboxes.addWidget(checkbox, r, c)
            self.export_as_checkboxes_list.append(checkbox)
       
        export_type_label_box = QHBoxLayout()
        export_type_label_box.addWidget(self.file_type_label)
        self.export_type_layout.addLayout(export_type_label_box)
        self.export_type_layout.addSpacing(10)
        self.export_type_layout.addLayout(self.export_as_checkboxes)
       
        combined_input_layout = QHBoxLayout()
        combined_input_layout.addSpacing(-20)
        combined_input_layout.addLayout(p_input_layout)
        combined_input_layout.addSpacing(-70)
        combined_input_layout.addLayout(t_input_layout)
       
        inputs_layout.addLayout(dropdown_layout)
        inputs_layout.addLayout(horizBox)
        inputs_layout.addLayout(choose_max_mins_layout)
        inputs_layout.addSpacing(150)
        inputs_layout.addLayout(combined_input_layout)
        inputs_layout.addLayout(self.graph_type_button_layout)
        inputs_layout.addLayout(self.select_graphtype_export_data_layout)
        inputs_layout.addLayout(self.export_type_layout)
       
        # Save options
        save_update_layout = QHBoxLayout()

        clear_graph_button = QPushButton("Clear")
        clear_graph_button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        clear_graph_button.setFixedWidth(100)
        clear_graph_button.clicked.connect(lambda: (self.clear_graph(self.graph_ax), self.graph_canvas.draw()))
        save_update_layout.addWidget(clear_graph_button)
       
        self.save_button = QPushButton("Save File")
        self.save_button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        self.save_button.setFixedWidth(100)
        self.save_button.clicked.connect(self.save_files)
        save_update_layout.addWidget(self.save_button)
 
        # Update graph button
        self.update_button = QPushButton("Update Graph")
        self.update_button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        self.update_button.setFixedWidth(100)
        self.update_button.clicked.connect(self.update_graph)
        save_update_layout.addWidget(self.update_button)

        # Import graph button
        self.import_button = QPushButton("Import Graph")
        self.import_button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        self.import_button.setFixedWidth(100)
        self.import_button.clicked.connect(self.import_graph)
        save_update_layout.addWidget(self.import_button)
       
        inputs_layout.addLayout(save_update_layout)
       
        # Add the inputs widget to the main layout (central_widget)
        self.central_widget.layout().addWidget(self.inputs_widget)
        return self.inputs_widget

    # Styles for centering
    class CenteredItemDelegate(QStyledItemDelegate):
        def paint(self, painter, option, index):
            option.displayAlignment = Qt.AlignmentFlag.AlignCenter
            super().paint(painter, option, index)

    # Updates the Select Material dropdown with appropriate height
    def update_dropdown(self, index):
        mat = self.dropdown.itemText(index)
        if mat in ['Ice Ih (0.1-400 MPa, 0.1-301 K)', 'Ice II (0.1-900 MPa, 0.1-270 K)',
                    'Ice III (0.1-500 MPa, 0.1-270 K)', 'Ice V (0.1-1000 MPa, 0.1-300 K)',
                    'Ice VI (0.1-3000 MPa, 0.1-400 K)']:
            self.dropdown.setFixedHeight(30)
        else:
            self.dropdown.setFixedHeight(50)

    # Adds graphtype labels to list for exporting later
    def graphtype_checkbox_state_changed(self, state):
        sender = self.sender()  # Get the checkbox that triggered the signal
        # 2 state means checked
        if state == 2:
            for label in self.graphtype_export_checkbox_labels:
                if sender.text() == label:
                    self.graphtype_export_checkboxes.append(label)
        # 0 state means unchecked
        elif state == 0:
            for label in self.graphtype_export_checkbox_labels:
                if sender.text() == label:
                    self.graphtype_export_checkboxes.remove(label)

    # Handles when txt json xlsx checkboxes are clicked
    def export_as_checkbox_state_changed(self, state):
        sender = self.sender()
        if state == 2:
            # Uncheck other checkboxes
            for checkbox in self.export_as_checkboxes_list:
                if checkbox != sender:
                    checkbox.setChecked(False)
            # Set export_type to the label of the checked checkbox
            self.export_type = sender.text()
        elif state == 0:
            # If the checkbox is unchecked, clear export_type if no other checkbox is checked
            self.export_type = ""
            for checkbox in self.export_as_checkboxes_list:
                if checkbox.isChecked():
                    self.export_type = checkbox.text()
                    break
    
    # Changes button color to gray
    def make_button_gray(self, button, color):
        button.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: 1px solid #A9A9A9")
        button.setMinimumHeight(30)
        self.current_button_mat = button

    # Changes button color back to normal
    def make_button_normal(self, button):
        button.setStyleSheet("border-radius: 5px; border: 1px solid #A9A9A9")
        self.current_button_mat = button

    # Changes button color to gray or normal
    # based on if it was clicked last or not
    def on_button_click(self, button):
        # Check if there's a previously clicked button and make it normal
        if self.current_button_mat is not None:
            self.make_button_normal(self.current_button_mat)

        # Make the clicked button gray
        self.make_button_gray(button, "#A9A9A9")

    # Changes the selected jules button color to gray
    def make_jules_button_gray(self, button, color):
        button.setStyleSheet(f"background-color: {color}; border-radius: 5px; border: 1px solid gray")
        button.setMinimumHeight(30)
        self.jmol_kg_button_mat = button

    # Changes the non-selected jules button color to normal
    def make_jules_button_normal(self, button):
        button.setStyleSheet("border-radius: 5px; border: 1px solid gray")
        self.jmol_kg_button_mat = button

    # Clears layouts
    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None and not (isinstance(widget, QLabel) or isinstance(widget, QComboBox)):
                    widget.setParent(None)
                else:
                    self.clear_layout(item.layout())

    # Sets selected graph type
    # and units for the main graph
    def get_material(self, label):
        self.selected_graph_type = label
        self.units = self.units_mapping.get(self.selected_graph_type, "")

    # Updates the material selected
    # from the dropdown
    def update_mat(self):
        self.mat = self.dropdown.currentText()
        try:
            if self.mat.splitlines()[1] == "(Bollengier et al. 2019)":
                self.material = "Liquid water 1"
            elif self.mat.splitlines()[1] == "(Abrahamson et al. 2004)":
                self.material = "Liquid water 2"
            elif self.mat.splitlines()[1] == "(IAPWS 95)":
                self.material = "Liquid water IAPWS_95"
        except IndexError:
            if self.mat == "Ice Ih (0.1-400 MPa, 0.1-301 K)":
                self.material = "Ice Ih"
            elif self.mat == "Ice II (0.1-900 MPa, 0.1-270 K)":
                self.material = "Ice II"
            elif self.mat == "Ice III (0.1-500 MPa, 0.1-270 K)":
                self.material = "Ice III"
            elif self.mat == "Ice V (0.1-1000 MPa, 0.1-300 K)":
                self.material = "Ice V"
            elif self.mat == "Ice VI (0.1-3000 MPa, 0.1-400 K)":
                self.material = "Ice VI"
        self.jkg_clicked_last = True
        self.jmol_clicked_last = True

    ## SINGLE POINT CALCULATOR

    # Initializes the Single Point Calculator
    def init_single_point_calculator_tab(self):
        layout = QVBoxLayout(self.calculator_tab)
        layout.addSpacing(50)
        top_label = QLabel("Choose Material via 'Select Material' on the Right\nThen Input Pressure and Temperature Values")
        top_label_font = top_label.font()
        top_label_font.setPointSize(12)
        top_label_font.setFamily("Arial")
        top_label.setFont(top_label_font)
        top_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(top_label)
        layout.addSpacing(30)

        self.content_layout = QVBoxLayout()  # New vertical layout for content

        p_t_layout = QHBoxLayout()
        self.p_t_input_boxes = [QLineEdit() for _ in range(2)]
        calc_labels = ["  Pressure (MPa)", "  Temperature (K)"]

        for label, input_box in zip(calc_labels, self.p_t_input_boxes):
            pair_layout = QVBoxLayout()  # Create a separate layout for each pair
            label_widget = QLabel(label)
            label_font = label_widget.font()
            label_font.setPointSize(10)
            label_font.setFamily("Arial")
            label_widget.setFont(label_font)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align label to the top
            pair_layout.addWidget(label_widget)
            
            hbox = QHBoxLayout()
            hbox.addSpacing(-6)
            hbox.addWidget(input_box)
            pair_layout.addLayout(hbox)
            input_box.setMaximumWidth(120)
            input_box.setStyleSheet("border: 1px solid #D3D3D3; border-radius: 5px; background: white; padding: 5px;")
            p_t_layout.addLayout(pair_layout)

        self.content_layout.addLayout(p_t_layout)  # Add the horizontal layout to the content layout
        self.content_layout.addSpacing(60)

        # Create a "Calculate" button
        calculate_button = QPushButton("Calculate")
        calculate_font = calculate_button.font()
        calculate_font.setPointSize(10)
        calculate_font.setFamily("Arial")
        calculate_button.setFont(calculate_font)
        calculate_button.setStyleSheet("background: gray; border-radius: 5px; border: 1px solid gray;")
        self.make_button_gray(calculate_button, "#A9A9A9")
        calculate_button.setMaximumWidth(150)
        hbox = QHBoxLayout()
        hbox.addSpacing(20)
        hbox.addWidget(calculate_button)

        self.content_layout.addSpacing(-30)
        calculate_button.clicked.connect(self.update_SPC_display)
        # Connect the Enter key press event for both input boxes to the update_display method
        # for input_box in self.p_t_input_boxes:
        #     input_box.returnPressed.connect(self.update_SPC_display)

        self.content_layout.addLayout(hbox)
       
        # Create a QTableWidget with 15 rows (properties) and 2 columns (property name and value)
        self.table_widget = QTableWidget(15, 2)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                border-radius: 5px;
                border: 1px solid #A9A9A9;
                background-color: #F5F5F5;
                gridline-color: #D3D3D3;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                selection-background-color: #ADD8E6;
            }
            
            QHeaderView::section {
                background-color: #D3D3D3;
                border: 1px solid #A9A9A9;
                padding: 5px;
                font-size: 14px;
                color: #333333;
            }
            
            QTableWidget::item {
                padding: 5px;
                border: none;
                color: #333333;
            }

            QTableWidget::item:selected {
                background-color: #87CEEB;
                color: #FFFFFF;
            }

            QTableCornerButton::section {
                background-color: #D3D3D3;
                border: 1px solid #A9A9A9;
            }
        """)
        self.table_widget.setHorizontalHeaderLabels(["Property", "Value"])
        # Set the width of the second column (index 1)
        for i in range (0,1):
            self.table_widget.setColumnWidth(i, 150)

        # Set the size policy and stretch factor for the table widget
        self.table_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table_widget.horizontalHeader().setStretchLastSection(True)

        space_before_table = 20
        self.content_layout.addSpacing(space_before_table)
        self.content_layout.addWidget(self.table_widget)

        layout.addLayout(self.content_layout)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setMinimumSectionSize(200)
        self.tab_widget.addTab(self.calculator_tab, "Single Point Calculator")

    # Re-sizes Single Point Calculator table
    def refresh_table_widget(self):
        # Remove the table widget and spacer from the layout if they exist
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            widget = item.widget()

            if widget == self.table_widget:
                self.content_layout.removeWidget(self.table_widget)
                self.table_widget.setParent(None)

        self.content_layout.addStretch(1)
        self.content_layout.addWidget(self.table_widget)

    # Updates the Single Point Calculator display
    def update_SPC_display(self):
        # Retrieve pressure and temperature values from input boxes
        pressure_text = self.p_t_input_boxes[0].text()
        temp_text = self.p_t_input_boxes[1].text()

        # Check if both input boxes have non-empty text
        if pressure_text and temp_text:
            # Convert the input values to integers
            pressure = np.double(pressure_text)
            temp = np.double(temp_text)
 
            # Evaluate thermodynamics for ice VI at the specified P and T
            PT = np.empty((1,), dtype='object')
            PT[0] = (pressure, temp)
            out = None
            if self.mat == None:
                return
            else:
                if self.mat == 'Liquid water\n(Bollengier et al. 2019)\n(0.1-2300 MPa, 239-501 K)':
                    out = sf.getProp(PT, 'water1')
                elif self.mat == 'Liquid water\n(IAPWS 95)\n(0.1-299.5 GPa, 180-19,993 K)':
                    out = sf.getProp(PT, 'water_IAPWS95')
                elif self.mat == 'Liquid water\n(Abrahamson et al. 2004)\n(0.1-100 GPa, 240-10,000 K)':
                    out = sf.getProp(PT, 'water2')
                elif self.mat == 'Ice Ih (0.1-400 MPa, 0.1-301 K)':
                    out = sf.getProp(PT, 'Ih')
                elif self.mat == 'Ice II (0.1-900 MPa, 0.1-270 K)':
                    out = sf.getProp(PT, 'II')
                elif self.mat == 'Ice III (0.1-500 MPa, 0.1-270 K)':
                    out = sf.getProp(PT, 'III')
                elif self.mat == 'Ice V (0.1-1000 MPa, 0.1-300 K)':
                    out = sf.getProp(PT, 'V')
                elif self.mat == 'Ice VI (0.1-3000 MPa, 0.1-400 K)':
                    out = sf.getProp(PT, 'VI')

        # Clear existing items in the table
        self.table_widget.clearContents()
        self.refresh_table_widget()

        # Define property names and corresponding out.x values
        if self.mat in self.ices:
            property_names = [
                "Gibb's Energy (J/kg)",
                "Entropy (J/K/kg)",
                "Enthalpy (J/kg)",
                "Internal Energy (J/kg)",
                "Specific Heat (Cp)",
                "Specific Heat (Cv)",
                "Density (kg/m^3)",
                "Isothermal Bulk Modulus (MPa)",
                "Isoentropic Bulk Modulus (MPa)",
                "Bulk Modulus Derivative - (unitless)",
                "Thermal Expansivity (1/K)",
                "Sound Speed (m/s)",
                "P Wave Velocity (solids)",
                "S Wave Velocity (solids)",
                "Shear Modulus (solids)",
            ]
            property_values = [
                out.G,       # Gibbs Energy J/kg
                out.S,       # Entropy J/K/kg
                out.H,       # Enthalpy J/kg
                out.U,       # Internal Energy J/kg
                out.Cp,      # Specific heat capacity at constant pressure J/kg/K
                out.Cv,      # Specific heat capacity at constant volume    J/kg/K
                out.rho,     # Density kg/m^3
                out.Kt,      # Isothermal Bulk Modulus MPa
                out.Ks,      # Isoentropic Bulk Modulus MPa
                out.Kp,      # Bulk Modulus Derivative - Kp unitless
                out.alpha,   # Thermal expansivity 1/K
                out.vel,     # Bulk Sound Speed
                out.Vp,      # P wave velocity
                out.Vs,      # S wave velocity
                out.shear    # Shear modulus
            ]
            self.table_widget.setRowCount(15)
            row_height = self.table_widget.verticalHeader().defaultSectionSize()
            self.table_widget.setFixedHeight(row_height * 15 + 2)
        else:
            property_names = [
                "Gibb's Energy (J/kg)",
                "Entropy (J/K/kg)",
                "Enthalpy (J/kg)",
                "Internal Energy (J/kg)",
                "Specific Heat (Cp)",
                "Specific Heat (Cv)",
                "Density (kg/m^3)",
                "Isothermal Bulk Modulus (MPa)",
                "Isoentropic Bulk Modulus (MPa)",
                "Bulk Modulus Derivative - (unitless)",
                "Thermal Expansivity (1/K)",
                "Sound Speed (m/s)",
            ]
            property_values = [
                out.G,       # Gibbs Energy J/kg
                out.S,       # Entropy J/K/kg
                out.H,       # Enthalpy J/kg
                out.U,       # Internal Energy J/kg
                out.Cp,      # Specific heat capacity at constant pressure J/kg/K
                out.Cv,      # Specific heat capacity at constant volume    J/kg/K
                out.rho,     # Density kg/m^3
                out.Kt,      # Isothermal Bulk Modulus MPa
                out.Ks,      # Isoentropic Bulk Modulus MPa
                out.Kp,      # Bulk Modulus Derivative - Kp unitless
                out.alpha,   # Thermal expansivity 1/K
                out.vel,     # Bulk Sound Speed
            ]
            self.table_widget.setRowCount(12)
            row_height = self.table_widget.verticalHeader().defaultSectionSize()
            self.table_widget.setFixedHeight((row_height + 4) * 12 + 2)
        # Populate the table with property names and values
        for row, (prop_name, prop_value) in enumerate(zip(property_names, property_values)):
            item_name = QTableWidgetItem(prop_name)
            item_value = QTableWidgetItem(str(prop_value).replace('[', '').replace(']', ''))

            # Set items in the table
            self.table_widget.setItem(row, 0, item_name)
            self.table_widget.setItem(row, 1, item_value)

    ## WATER PHASE DIAGRAM

    # Initializes the Water Phase Diagram tab
    def init_WP_Diagram_Tab(self):
        WPD_graph_box = QVBoxLayout()

        # Create a horizontal layout to center the toolbar
        toolbar_layout = QHBoxLayout()
        toolbar = NavigationToolbar(self.WP_canvas, self)

        # Add the toolbar to the horizontal layout and center it
        toolbar_layout.addWidget(toolbar, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Add some vertical space (adjust the height as needed)
        spacer = QSpacerItem(0, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)  # 40px spacer
        WPD_graph_box.addItem(spacer)

        # Add the toolbar layout below the spacer
        WPD_graph_box.addLayout(toolbar_layout)

        # Add the graph canvas below the toolbar
        WPD_graph_box.addWidget(self.WP_canvas)

        # Create a layout for the sections
        sections_horizontal_container = QHBoxLayout()
        sections_layout = QVBoxLayout()

        hbox = QHBoxLayout()
        options_label = QLabel("Choose Plot/Export Options")
        options_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
            }
        """
        )
        options_label.setFixedSize(250, 30)
        hbox.addWidget(options_label)
        sections_layout.addLayout(hbox)

        # Create a layout for melting curves section
        melting_section = QVBoxLayout()
        m_label_box = QHBoxLayout()
        melting_boxes = QGridLayout()
        melting_curves_label = QLabel("Melting Curves")
        melting_curves_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
            }
        """
        )
        melting_curves_label.setFixedSize(120, 40)
        m_label_box.addWidget(melting_curves_label)
        melting_section.addLayout(m_label_box)
        self.melting_curve_checkboxes = {
            "Ih/Liquid": QCheckBox("Ih/Liquid"),
            "III/Liquid": QCheckBox("III/Liquid"),
            "V/Liquid": QCheckBox("V/Liquid"),
            "VI/Liquid": QCheckBox("VI/Liquid")
        }
        boxes_per_column = 2
        for i, (checkbox_name, checkbox) in enumerate(self.melting_curve_checkboxes.items()):
            row = i % boxes_per_column
            col = i // boxes_per_column
            melting_boxes.addWidget(checkbox, row, col)
            self.WP_plotting_checkboxes[checkbox_name] = False
            self.checkbox_data_map[checkbox_name] = checkbox_name
            checkbox.stateChanged.connect(lambda state, name=checkbox_name: self.WP_plotting_checkbox_checked(name, state))
            checkbox.setStyleSheet("""
            QCheckBox::indicator:unchecked {
                border: 1px solid #D3D3D3;
                background: white;
                border-radius: 5px;
                width: 15px;
                height: 15px;
            }
            QCheckBox {
                font-size: 14px;
            }                  
            """)
            checkbox.setFixedSize(100, 30)
        melting_section.addLayout(melting_boxes)

        # Create a layout for solid-solid transitions section
        solid_section = QVBoxLayout()
        s_label_box = QHBoxLayout()
        solid_boxes = QGridLayout()
        solid_solid_label = QLabel("Solid-Solid Transitions")
        solid_solid_label.setFixedSize(170, 40)
        solid_solid_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
            }
        """
        )
        s_label_box.addWidget(solid_solid_label)
        solid_section.addLayout(s_label_box)
        self.solid_solid_checkboxes = {
            "Ih/II": QCheckBox("Ih/II"),
            "Ih/III": QCheckBox("Ih/III"),
            "II/V": QCheckBox("II/V"),
            "II/VI": QCheckBox("II/VI"),
            "II/III": QCheckBox("II/III"),
            "III/V": QCheckBox("III/V"),
            "V/VI": QCheckBox("V/VI")
        }
        boxes_per_column = 2
        for i, (checkbox_name, checkbox) in enumerate(self.solid_solid_checkboxes.items()):
            row = i % boxes_per_column
            col = i // boxes_per_column
            solid_boxes.addWidget(checkbox, row, col)
            self.WP_plotting_checkboxes[checkbox_name] = False
            self.checkbox_data_map[checkbox_name] = checkbox_name
            checkbox.stateChanged.connect(lambda state, name=checkbox_name: self.WP_plotting_checkbox_checked(name, state))
            checkbox.setStyleSheet("""
            QCheckBox::indicator:unchecked {
                border: 1px solid #D3D3D3;
                background: white;
                border-radius: 5px;
                width: 15px;
                height: 15px;
            }
            QCheckBox {
                font-size: 14px;
            }                  
            """)
            checkbox.setFixedSize(80, 30)
        solid_section.addLayout(solid_boxes)

        # Create a layout for export options
        export_section = QVBoxLayout()
        e_label_box = QHBoxLayout()
        export_boxes = QGridLayout()
        export_label = QLabel("Export As:")
        export_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
            }
        """
        )
        export_label.setFixedSize(75, 40)
        e_label_box.addWidget(export_label)
        export_section.addLayout(e_label_box)
        self.WPD_export_checkboxes = {
            "Triple-Point(s)": self.triple_points_checkbox, "Delta H and S": self.delta_h_s_checkbox,
            "DeltaV": self.delta_v_checkbox, ".txt": self.WP_txt_checkbox
        }
        boxes_per_column = 2
        for i, (checkbox_name, checkbox) in enumerate(self.WPD_export_checkboxes.items()):
            row = i % boxes_per_column
            col = i // boxes_per_column
            export_boxes.addWidget(checkbox, row, col)
            self.checkbox_data_map[checkbox_name] = checkbox_name
            checkbox.setStyleSheet("""
            QCheckBox::indicator:unchecked {
                border: 1px solid #D3D3D3;
                background: white;
                border-radius: 5px;
                font-size: 10px;
                width: 15px;
                height: 15px;
            }
            QCheckBox {
                font-size: 14px;
            }
            """)
            checkbox.setFixedSize(110, 40)
        export_section.addLayout(export_boxes)

        # Create a layout for plot and export buttons
        button_layout = QHBoxLayout()

        clear_WP_button = QPushButton("Clear")
        clear_WP_button.setStyleSheet("border-radius: 10px; border: 1px solid gray")
        clear_WP_button.setFixedSize(50, 30)
        clear_WP_button.clicked.connect(lambda: (self.clear_graph(self.WP_ax), self.WP_canvas.draw()))

        self.plot_complete_button = QPushButton("Plot Complete\nWater Phase Diagram")
        self.plot_complete_button.setStyleSheet("border-radius: 10px; border: 1px solid gray")
        self.plot_complete_button.setFixedSize(130, 40)
        self.plot_complete_button.clicked.connect(self.plot_complete_phase_diagram)
        self.plot_complete_button.clicked.connect(lambda: complete_clicked(True))

        def complete_clicked(value):
            self.plot_complete_button_clicked = value
        def curves_clicked(value):
            self.plot_curves_button_clicked = value
            self.plot_complete_button_clicked = not value

        plot_button = QPushButton("Plot Selected\nCurves")
        plot_button.setStyleSheet("border-radius: 10px; border: 1px solid gray")
        plot_button.setFixedSize(80, 40)
        plot_button.clicked.connect(self.draw_phaselines)
        plot_button.clicked.connect(lambda: curves_clicked(True))

        export_button = QPushButton("Export")
        export_button.setStyleSheet("border-radius: 10px; border: 1px solid gray")
        export_button.setFixedSize(60, 30)
        export_button.clicked.connect(self.export_WPD_data)

        button_layout.addWidget(clear_WP_button)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.plot_complete_button)
        button_layout.addSpacing(20)
        button_layout.addWidget(plot_button)
        button_layout.addSpacing(20)
        button_layout.addWidget(export_button)
        
        # Add the sections to the sections_layout
        sections_layout.addLayout(melting_section)
        sections_layout.addLayout(solid_section)
        sections_layout.addLayout(export_section)
        sections_layout.addLayout(button_layout)

        self.layout_WP.addLayout(WPD_graph_box)
        sections_horizontal_container.addLayout(sections_layout)
        self.layout_WP.addLayout(sections_horizontal_container)

        # Set the layout for the tab
        self.WP_tab.setLayout(self.layout_WP)
        # Add the WP_tab to the tab_widget
        self.tab_widget.addTab(self.WP_tab, "Water Phase Diagram")

    # Activates/deactivates phaseline checkbox for graphing
    def WP_plotting_checkbox_checked(self, name, state):
        for i, (checkbox_name, _) in enumerate(self.checkedPhaselines):
            if checkbox_name == name:
                self.checkedPhaselines[i] = (name, state)
                break

    # Plots the foundational points
    # for the Water Phase Diagram graph
    def plot_complete_phase_diagram(self):
        self.WP_ax.clear()
       
        solid_solid = self.WP_data['Solid_Solid']
        melt_line = self.WP_data['Melt_Line']

        # Plot melt lines and store data points
        # TP_Ih_water1
        melt_Ih_water1_x = melt_line['TP_Ih_water1'][0][0][1, :]
        melt_Ih_water1_y = melt_line['TP_Ih_water1'][0][0][0, :]
        self.WP_ax.plot(melt_Ih_water1_x, melt_Ih_water1_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((melt_Ih_water1_x, melt_Ih_water1_y))

        # TP_III_water1
        melt_III_water1_x = melt_line['TP_III_water1'][0][0][1, :]
        melt_III_water1_y = melt_line['TP_III_water1'][0][0][0, :]
        self.WP_ax.plot(melt_III_water1_x, melt_III_water1_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((melt_III_water1_x, melt_III_water1_y))

        # TP_V_water1
        melt_V_water1_x = melt_line['TP_V_water1'][0][0][1, :]
        melt_V_water1_y = melt_line['TP_V_water1'][0][0][0, :]
        self.WP_ax.plot(melt_V_water1_x, melt_V_water1_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((melt_V_water1_x, melt_V_water1_y))

        # TP_VI_water1
        melt_VI_water1_x = melt_line['TP_VI_water1'][0][0][1, :]
        melt_VI_water1_y = melt_line['TP_VI_water1'][0][0][0, :]
        self.WP_ax.plot(melt_VI_water1_x, melt_VI_water1_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((melt_VI_water1_x, melt_VI_water1_y))

        # Plot solid-solid transitions and store data points
        # TP_Ih_II (dashed before point 208)
        Ih_II_x_1 = solid_solid['TP_Ih_II'][0][0][1, 0:208]
        Ih_II_y_1 = solid_solid['TP_Ih_II'][0][0][0, 0:208]
        self.WP_ax.plot(Ih_II_x_1, Ih_II_y_1, '--', color='blue', alpha=0.65)
        self.complete_diagram_points.append((Ih_II_x_1, Ih_II_y_1))

        # TP_Ih_II (solid after point 208)
        Ih_II_x_2 = solid_solid['TP_Ih_II'][0][0][1, 208:655]
        Ih_II_y_2 = solid_solid['TP_Ih_II'][0][0][0, 208:655]
        self.WP_ax.plot(Ih_II_x_2, Ih_II_y_2, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((Ih_II_x_2, Ih_II_y_2))

        # TP_Ih_III
        Ih_III_x = solid_solid['TP_Ih_III'][0][0][1,:]
        Ih_III_y = solid_solid['TP_Ih_III'][0][0][0,:]
        self.WP_ax.plot(Ih_III_x, Ih_III_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((Ih_III_x, Ih_III_y))

        # TP_II_III
        II_III_x = solid_solid['TP_II_III'][0][0][1,:]
        II_III_y = solid_solid['TP_II_III'][0][0][0,:]
        self.WP_ax.plot(II_III_x, II_III_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((II_III_x, II_III_y))

        # TP_II_V
        II_V_x = solid_solid['TP_II_V'][0][0][1, 0:]
        II_V_y = solid_solid['TP_II_V'][0][0][0, 0:]
        self.WP_ax.plot(II_V_x, II_V_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((II_V_x, II_V_y))

        # TP_II_VI (solid after point 505)
        II_VI_x_1 = solid_solid['TP_II_VI'][0][0][1, 505:]
        II_VI_y_1 = solid_solid['TP_II_VI'][0][0][0, 505:]
        self.WP_ax.plot(II_VI_x_1, II_VI_y_1, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((II_VI_x_1, II_VI_y_1))

        # TP_II_VI (dashed before point 505)
        II_VI_x_2 = solid_solid['TP_II_VI'][0][0][1, 0:505]
        II_VI_y_2 = solid_solid['TP_II_VI'][0][0][0, 0:505]
        self.WP_ax.plot(II_VI_x_2, II_VI_y_2, '--', color='blue', alpha=0.65)
        self.complete_diagram_points.append((II_VI_x_2, II_VI_y_2))

        # TP_III_V
        III_V_x = solid_solid['TP_III_V'][0][0][1, 0:]
        III_V_y = solid_solid['TP_III_V'][0][0][0, 0:]
        self.WP_ax.plot(III_V_x, III_V_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((III_V_x, III_V_y))

        # TP_V_VI
        V_VI_x = solid_solid['TP_V_VI'][0][0][1, 0:]
        V_VI_y = solid_solid['TP_V_VI'][0][0][0, 0:]
        self.WP_ax.plot(V_VI_x, V_VI_y, '-', color='blue', alpha=0.65)
        self.complete_diagram_points.append((V_VI_x, V_VI_y))

        # Plot circles (triple points)
        for circles in self.circles_dict.values():
            for circle in circles:
                self.WP_ax.plot(circle[0], circle[1], marker='o',
                                color='blue', markerfacecolor='none', markersize=8, alpha=0.65)
        self.create_legend()
        self.WP_ax.set_xlim(0, 2300)
        self.WP_ax.set_ylim(0, 375)
        self.WP_labels()
        self.WP_canvas.draw()
        self.total_points += self.complete_diagram_points

    # Creates legend for WPD
    def create_legend(self):
        # Plot dummy data to set up static legend
        dummy_line_solid = mlines.Line2D([], [], color='blue', linestyle='-', alpha=0.65, label='Solid')
        dummy_line_meta = mlines.Line2D([], [], color='blue', linestyle='--', alpha=0.65, label='Metastable Extension')
        dummy_line_triple = mlines.Line2D([], [], color='blue', marker='o', markerfacecolor='none', markersize=8, alpha=0.65, label='Triple Points')
        
        # Add the dummy lines to the axes
        self.WP_ax.add_line(dummy_line_solid)
        self.WP_ax.add_line(dummy_line_meta)
        self.WP_ax.add_line(dummy_line_triple)

    # Plots V/VI phaseline
    def phaseline_plot_V_VI(self, contour, circles):
        # Sort circles by their Y-values (second element)
        circles = sorted(circles, key=lambda x: x[1])

        # Step 1: Plot the path segments
        for level_paths in contour.allsegs:
            for path_segment in level_paths:
                path_segment = np.array(path_segment)
                # Initialize list to store indices of points closest to circles
                indices = []

                # Find indices of points closest to each circle
                for circle in circles:
                    dist = np.sqrt((path_segment[:, 0] - circle[0])**2 + (path_segment[:, 1] - circle[1])**2)
                    closest_index = np.argmin(dist)
                    indices.append(closest_index)

                # Sort indices to ensure segments are split correctly
                indices = sorted(set(indices))

                # Step 2: Plot segments before, between, and after circles
                if indices:
                    # Dashed line before the first circle
                    self.WP_ax.plot(path_segment[:indices[0], 0], path_segment[:indices[0], 1], 
                                    color='blue', linestyle='--', alpha=0.65, zorder=1)

                    # Solid line between each pair of circles
                    for i in range(len(indices) - 1):
                        self.WP_ax.plot(path_segment[indices[i]:indices[i+1], 0], path_segment[indices[i]:indices[i+1], 1],
                                        color='blue', linestyle='-', alpha=0.85, zorder=2)

                    # Dashed line after the last point before the second circle (sorted by Y-value)
                    second_circle_index = indices[-1]  # This should be the last circle in Y-sorted order
                    self.WP_ax.plot(path_segment[second_circle_index:, 0], path_segment[second_circle_index:, 1],
                                    color='blue', linestyle='--', alpha=0.65, zorder=1)
                else:
                    # If no circles are found on the path, keep the whole line dashed
                    self.WP_ax.plot(path_segment[:, 0], path_segment[:, 1], 
                                    color='blue', linestyle='--', alpha=0.65, zorder=1)

        # Step 3: Plot circles (triple points)
        for circle in circles:
            self.WP_ax.plot(circle[0], circle[1], marker='o',
                            color='blue', markerfacecolor='none', markersize=8, alpha=0.65)

        self.WP_labels()

    # Plots II/VI phaseline
    def phaseline_plot_II_VI(self, contour, circles):
        # Reverse the circles list to process from left to right
        circles = circles[::-1]
        
        # Extract x-coordinates of circles
        circle_x_coords = [circle[0] for circle in circles]
        
        # Iterate through all paths in the contour
        for level_paths in contour.allsegs:
            for path_segment in level_paths:
                # Lists to hold points before, between, and after circles
                before = []
                between = []
                after = []
                
                # Classify points based on their x-coordinate
                for point in path_segment:
                    point_x = point[0]
                    
                    if len(circles) == 1:
                        # If only one circle exists
                        if point_x < circle_x_coords[0]:
                            before.append(point)
                        else:
                            after.append(point)
                    else:
                        # If multiple circles exist
                        if point_x < circle_x_coords[0]:
                            before.append(point)
                        elif circle_x_coords[0] <= point_x <= circle_x_coords[-1]:
                            between.append(point)
                        else:
                            after.append(point)

                # Plot solid and metastable extension lines
                if len(circles) == 1:
                    if len(before) > 0:
                        # Plot solid lines for points before the circle
                        self.WP_ax.plot(np.array(before)[:, 0], np.array(before)[:, 1], 
                                        color='blue', linestyle='--', alpha=0.65)
                    if len(after) > 0:
                        # Plot metastable extension lines for points after the circle
                        self.WP_ax.plot(np.array(after)[:, 0], np.array(after)[:, 1], 
                                        color='blue', linestyle='-', alpha=0.65)
                else:
                    if len(between) > 0:
                        # Plot solid lines for points between circles
                        self.WP_ax.plot(np.array(between)[:, 0], np.array(between)[:, 1], 
                                        color='blue', linestyle='-', alpha=0.65)
                    if len(before) > 0:
                        # Plot metastable extension lines for points before circles
                        self.WP_ax.plot(np.array(before)[:, 0], np.array(before)[:, 1], 
                                        color='blue', linestyle='--', alpha=0.65)
                    if len(after) > 0:
                        # Plot metastable extension lines for points after circles
                        self.WP_ax.plot(np.array(after)[:, 0], np.array(after)[:, 1], 
                                        color='blue', linestyle='-', alpha=0.65)
        
        # Plot circles (triple points)
        for circle in circles:
            self.WP_ax.plot(circle[0], circle[1], marker='o',
                            color='blue', markerfacecolor='none', markersize=8, alpha=0.65)
        self.WP_labels()

    # Plots the solid-dashed contour line for each checkbox
    def phaseline_plot_and_style(self, contour, circles):
        # Reverse the circles list to process from left to right
        circles = circles[::-1]
        
        # Extract x-coordinates of circles
        circle_x_coords = [circle[0] for circle in circles]
        
        # Iterate through all paths in the contour
        for level_paths in contour.allsegs:
            for path_segment in level_paths:
                # Lists to hold points before, between, and after circles
                before = []
                between = []
                after = []
                
                # Classify points based on their x-coordinate
                for point in path_segment:
                    point_x = point[0]
                    
                    if len(circles) == 1:
                        # If only one circle exists
                        if point_x < circle_x_coords[0]:
                            before.append(point)
                        else:
                            after.append(point)
                    else:
                        # If multiple circles exist
                        if point_x < circle_x_coords[0]:
                            before.append(point)
                        elif circle_x_coords[0] <= point_x <= circle_x_coords[-1]:
                            between.append(point)
                        else:
                            after.append(point)

                # Plot solid and metastable extension lines
                if len(circles) == 1:
                    if len(before) > 0:
                        # Plot solid lines for points before the circle
                        self.WP_ax.plot(np.array(before)[:, 0], np.array(before)[:, 1], 
                                        color='blue', linestyle='-', alpha=0.65)
                    if len(after) > 0:
                        # Plot metastable extension lines for points after the circle
                        self.WP_ax.plot(np.array(after)[:, 0], np.array(after)[:, 1], 
                                        color='blue', linestyle='--', alpha=0.65)
                else:
                    if len(between) > 0:
                        # Plot solid lines for points between circles
                        self.WP_ax.plot(np.array(between)[:, 0], np.array(between)[:, 1], 
                                        color='blue', linestyle='-', alpha=0.65)
                    if len(before) > 0:
                        # Plot metastable extension lines for points before circles
                        self.WP_ax.plot(np.array(before)[:, 0], np.array(before)[:, 1], 
                                        color='blue', linestyle='--', alpha=0.65)
                    if len(after) > 0:
                        # Plot metastable extension lines for points after circles
                        self.WP_ax.plot(np.array(after)[:, 0], np.array(after)[:, 1], 
                                        color='blue', linestyle='--', alpha=0.65)
        
        # Plot circles (triple points)
        for circle in circles:
            self.WP_ax.plot(circle[0], circle[1], marker='o',
                            color='blue', markerfacecolor='none', markersize=8, alpha=0.65)
        self.WP_labels()

    # Draws Phaselines according to checkboxes
    def draw_phaselines(self):
        self.complete_diagram_points = []
        self.circles = {}
        self.contours = {}

        for checkbox_name, status in self.checkedPhaselines:
            if status == 2 and checkbox_name in self.circles_dict:
                match (checkbox_name):
                    case "Ih/Liquid":
                        (P, T, Z) = phaselines.phaselines('Ih', 'water1')
                    case "III/Liquid":
                        (P, T, Z) = phaselines.phaselines('III', 'water1')
                    case "V/Liquid":
                        (P, T, Z) = phaselines.phaselines('V', 'water1')
                    case "VI/Liquid":
                        (P, T, Z) = phaselines.phaselines('VI', 'water1')
                    case "Ih/II":
                        (P, T, Z) = phaselines.phaselines('Ih', 'II')
                    case "Ih/III":
                        (P, T, Z) = phaselines.phaselines('Ih', 'III')
                    case "II/III":
                        (P, T, Z) = phaselines.phaselines('II', 'III')
                    case "II/V":
                        (P, T, Z) = phaselines.phaselines('II', 'V')
                    case "II/VI":
                        (P, T, Z) = phaselines.phaselines('II', 'VI')
                    case "III/V":
                        (P, T, Z) = phaselines.phaselines('III', 'V')
                    case "V/VI":
                        (P, T, Z) = phaselines.phaselines('V', 'VI')
                    case _:
                        return

                circles = self.circles_dict[checkbox_name]
                self.circles[checkbox_name] = circles
                contour = self.WP_ax.contour(P, T, Z, levels=[0], colors='blue')
                self.contours[checkbox_name] = contour

            else:
                if checkbox_name in self.contours:
                    self.contours.pop(checkbox_name, None)

        # Clear the axes and re-plot all contours and circles
        self.WP_ax.clear()
        self.create_legend()
        for mat, contour in self.contours.items():
            if mat == "V/VI":
                self.phaseline_plot_V_VI(contour, self.circles[mat])
            elif mat == "II/VI":
                self.phaseline_plot_II_VI(contour, self.circles[mat])
            else:
                self.phaseline_plot_and_style(contour, self.circles[mat])
        if not mat == "V/VI":
            self.WP_ax.set_xlim(left=0)
        self.WP_ax.set_xlabel('Pressure (MPa)')
        self.WP_ax.set_ylabel('Temperature (K)')
        self.WP_canvas.draw()

    # Labels the Water Phase Diagram graph
    def WP_labels(self):
        legend = self.WP_ax.legend(loc='best', fontsize=8)
        frame = legend.get_frame()
        frame.set_edgecolor('black')
        frame.set_linewidth(1)

        if len(self.complete_diagram_points) > 0:
            self.WP_ax.text(50, 175, 'Ih', fontsize=12)
            self.WP_ax.text(300, 300, 'Liquid Water', fontsize=12)
            self.WP_ax.text(400, 200, 'II', fontsize=12)
            self.WP_ax.text(260, 250, 'III', fontsize=12)
            self.WP_ax.text(525, 250, 'V', fontsize=12)
            self.WP_ax.text(1000, 250, 'VI', fontsize=12)
 
        self.WP_ax.set_xlabel('Pressure (MPa)')
        self.WP_ax.set_ylabel('Temperature (K)')
        self.WP_ax.set_title("Water Phase Diagram")

    # Tracks mouse movement over the plot.
    # Finds and annotates the closest point if within a distance threshold.
    # Hides the annotation and marker if no point is close enough.
    def on_mouse_motion(self, event):
        if event.inaxes == self.WP_ax:
            x, y = event.xdata, event.ydata  # Get the current mouse position

            min_distance = float('inf')
            closest_point = None

            # Loop through each line in the plot and find the closest point to the cursor
            for line in self.WP_ax.get_lines():
                line_xdata, line_ydata = line.get_data()

                if np.array(line_xdata).size > 0 and np.array(line_ydata).size > 0:
                    closest_index = np.argmin(np.sqrt((line_xdata - x)**2 + (line_ydata - y)**2))
                    point_x, point_y = line_xdata[closest_index], line_ydata[closest_index]

                    distance = np.sqrt((point_x - x)**2 + (point_y - y)**2)

                    # Update the closest point if necessary
                    if distance < min_distance:
                        min_distance = distance
                        closest_point = (point_x, point_y)

                    self.total_points.extend(zip(line_xdata, line_ydata))  # Add points to total

            # Define a distance threshold for displaying the annotation
            distance_threshold = 5 if not self.complete_diagram_points else 20

            # If a point is within the threshold, update the marker and annotation
            if closest_point and min_distance <= distance_threshold:
                if hasattr(self, 'cursor_marker') and self.cursor_marker in self.WP_ax.collections:
                    self.cursor_marker.remove()

                self.annotate_cursor_position(closest_point[0], closest_point[1])
                self.WP_canvas.draw_idle()

            # Hide annotation and remove the marker if no point is close enough
            else:
                if self.cursor_marker:
                    self.cursor_marker.remove()
                    self.cursor_marker = None

                if self.cursor_annotation:
                    self.cursor_annotation.set_visible(False)
                    self.WP_canvas.draw_idle()
        
        # Hide annotation if the mouse is not within the plot
        elif self.cursor_annotation and self.cursor_annotation.get_visible():
            self.cursor_annotation.set_visible(False)
            self.WP_canvas.draw_idle()

    # Calculates x and y offsets for annotations based on axis scaling.
    def calculate_offsets(self):
        xlim = self.WP_ax.get_xlim()
        ylim = self.WP_ax.get_ylim()
        
        # Scale x and y axes for offset calculation
        x_scale = (xlim[1] - xlim[0]) / 100
        y_scale = (ylim[1] - ylim[0]) / 100
        
        # Adjust multipliers to fine-tune offsets
        x_multiplier = 2.0
        y_multiplier = 2.5
        
        return x_scale * x_multiplier, y_scale * y_multiplier

    # Annotates the cursor's x, y position with a label and plots a red circle.
    def annotate_cursor_position(self, x, y):
        self.cursor_x = x
        self.cursor_y = y

        # Remove previous annotation and marker if they exist
        if self.cursor_annotation is not None:
            self.cursor_annotation.remove()

        if hasattr(self, 'cursor_marker') and self.cursor_marker in self.WP_ax.collections:
            self.cursor_marker.remove()
            self.cursor_marker = None

        # Plot the red circle at the point
        self.cursor_marker = self.WP_ax.scatter(self.cursor_x, self.cursor_y, s=50, c='red', marker='o', zorder=5)

        # Annotate with offset based on the x-axis scaling
        annotation_text = f'({self.cursor_x:.4f}, {self.cursor_y:.4f})'
        offset_x, offset_y = self.calculate_offsets()
        self.cursor_annotation = self.WP_ax.annotate(
            annotation_text,
            xy=(self.cursor_x, self.cursor_y),
            xytext=(self.cursor_x + offset_x, self.cursor_y + offset_y),
            bbox=dict(boxstyle='round, pad=0.5', edgecolor='white', facecolor='white'),
            fontsize=10,
            visible=True,
        )

        self.WP_canvas.draw_idle()

    # Removes red dot
    def remove_red_dot(self):
        if hasattr(self, 'cursor_marker') and self.cursor_marker is not None:
            if self.cursor_marker in self.WP_ax.collections:
                self.cursor_marker.remove()
                self.cursor_marker = None
        self.WP_canvas.draw_idle()

    # Saves the base file with updated header and suffix, then writes to a new file.
    def save_base_file(self, file_path, directory_path, checkbox_name, suffix):
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                lines[0] = "SF_Version 1.0.1\n"
                lines[1] = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
                if suffix in ["_D_S_H_WPD", "_D_S_H"]:
                    lines[5] = lines[5].strip() + ")" + "\n"

                output_file_path = f"{directory_path}/{checkbox_name.replace('/', '_')}{suffix}.txt"
                with open(output_file_path, "w") as f:
                    f.writelines(lines)
                print(f"Saved as Text: {output_file_path}")
        except Exception:
            return

    # Saves the base files and conditionally additional files based on checkbox selections.
    def save_base_files(self, checkbox_name, directory_path):
        basefile_mapping = {
            "Ih/Liquid": "Ih_water1",
            "III/Liquid": "III_water1",
            "V/Liquid": "V_water1",
            "VI/Liquid": "VI_water1",
            "Ih/II": "Ih_II",
            "Ih/III": "Ih_III",
            "II/V": "II_V",
            "II/VI": "II_VI",
            "II/III": "II_III",
            "III/V": "III_V",
            "V/VI": "V_VI",
        }
        basefile = basefile_mapping.get(checkbox_name, "")
        if not basefile:
            return  # Skip if there's no mapping for the checkbox name

        base_file_path = f"WPD-files/{basefile}.txt"
        D_S_H_file_path = f"WPD-files/{basefile}_D_S_H.txt"
        DV_file_path = f"WPD-files/{basefile}_DV.txt"

        # Save base file for all cases
        self.save_base_file(base_file_path, directory_path, checkbox_name, "")

        # Conditionally save additional files based on checkboxes
        if self.delta_h_s_checkbox.isChecked():
            self.save_base_file(D_S_H_file_path, directory_path, checkbox_name, "_D_S_H")

        if self.delta_v_checkbox.isChecked():
            self.save_base_file(DV_file_path, directory_path, checkbox_name, "_DV")

    # Exports WPD data
    # Handles Triple Points, Delta H/S, and Delta V file exports
    def export_WPD_data(self):
        try:
            directory_path = QFileDialog().getExistingDirectory(None, "Select Directory", options=QFileDialog.Option.ShowDirsOnly)
            if not directory_path:
                return  # If the user cancels the directory selection, exit the function

            base_path = "WPD-files/TriplePoints"
            path_All = "WPD-files/All_Triple_Points.txt"
            current_index = self.tab_widget.currentIndex()
            current_tab_name = self.tab_widget.tabText(current_index)
            triple_point_suffixes = {
                "Ih/II": "_Ih_II.txt", "Ih/III": "_Ih_III.txt",
                "Ih/Liquid": "_Ih_water1.txt", "II/III": "_II_III.txt",
                "II/V": "_II_V.txt", "II/VI": "_II_VI.txt",
                "III/V": "_III_V.txt", "III/Liquid": "_III_water1.txt",
                "V/VI": "_V_VI.txt", "V/Liquid": "_V_water1.txt",
                "VI/Liquid": "_VI_water1.txt"
            } if current_tab_name == "Water Phase Diagram" else None

            any_checked = any(status == 2 for _, status in self.checkedPhaselines)

            if any_checked:
                # Save files for checked phaseline boxes
                for checkbox_name, status in self.checkedPhaselines:
                    if status == 2:
                        self.save_base_files(checkbox_name, directory_path)
                        suffix = triple_point_suffixes[checkbox_name]
                        
                        if self.triple_points_checkbox.isChecked():
                            self.save_Triple_Points(base_path + suffix, directory_path, suffix)

            if self.plot_complete_button_clicked:
                # Save files if plot complete button is clicked
                for checkbox_name, status in self.checkedPhaselines:
                    self.save_base_files(checkbox_name, directory_path)

                if self.triple_points_checkbox.isChecked():
                    self.save_Triple_Points(path_All, directory_path, "")

                for checkbox_name, suffix in triple_point_suffixes.items():
                    suffix = suffix.replace(".txt", "").replace("/", "_").lstrip("_")
                    if self.delta_h_s_checkbox.isChecked():
                        self.save_base_file(f"WPD-files/{suffix}_D_S_H_WPD.txt", directory_path, checkbox_name, "_D_S_H_WPD")

                    if self.delta_v_checkbox.isChecked():
                        self.save_base_file(f"WPD-files/{suffix}_DV_WPD.txt", directory_path, checkbox_name, "_DV_WPD")
        except Exception:
            return

    # Saves 'All_Triple_Points' or specific triple point files.
    def save_Triple_Points(self, file_path, directory_path, suffix):
        if file_path.endswith("All_Triple_Points.txt"):
            file_name = "All_Triple_Points.txt"
        else:
            file_name = f"TriplePoints{suffix}"
        
        output_path = f"{directory_path}/{file_name}"
        
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()
                lines[0] = "SF_Version 1.0.1\n"
                lines[1] = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
                with open(output_path, "w") as f:
                    f.writelines(lines)
            
            print(f"Saved Triple Points: {output_path}")
        except Exception:
            return

    ## MORE
    def init_more_tab(self):
        # Create a "More" tab
        more_tab = QWidget()
        more_layout = QVBoxLayout(more_tab)
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        # Create a "Help" button
        help_button = QPushButton("Help")
        help_button.setStyleSheet("border-radius: 5px; border: 1px solid gray;")
        help_button.clicked.connect(self.open_github_page)
        help_button.setFixedSize(75, 25)
        hbox.addWidget(help_button)
        hbox.addStretch(1)
        more_layout.addSpacing(40)
        more_layout.addLayout(hbox)
        self.tab_widget.addTab(more_tab, "More")

        reference_text = """
        <div align="center">
            <b>Reference to cite to use SeaFreeze:</b>
            <br>
            <br>
            <a href="https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019JE006176">
            Journaux et al. (2020) JGR Planets 125(1), e2019JE006176</a>
            <br>
            <br>
            <br>
            <br>
            <b>References for the liquid water equations of states used:</b>
            <a href="https://pubs.aip.org/aip/jcp/article/151/5/054501/198554/Thermodynamics-of-pure-liquid-water-Sound-speed">
            <br>
            <br>
            Bollengier, Brown and Shaw (2019) J. Chem. Phys. 151, 054501; doi: 10.1063/1.5097179</a>
            <a href="https://www.sciencedirect.com/science/article/abs/pii/S0378381218300530">
            <br>
            <br>
            Brown (2018) Fluid Phase Equilibria 463, pp. 18-31</a>
            <a href="https://pubs.aip.org/aip/jpr/article-abstract/35/2/1021/242042/A-New-Equation-of-State-for-H2O-Ice-Ih?redirectedFrom=fulltext">
            <br>
            <br>
            Feistel and Wagner (2006), J. Phys. Chem. Ref. Data 35, pp. 1021-1047</a>
            <a href="https://pubs.aip.org/aip/jpr/article-abstract/31/2/387/241937/The-IAPWS-Formulation-1995-for-the-Thermodynamic?redirectedFrom=fulltext">
            <br>
            <br>
            Wagner and Pruss (2002), J. Phys. Chem. Ref. Data 31, pp. 387-535</a>
            <a href="https://journals.aps.org/prb/abstract/10.1103/PhysRevB.91.014308">
            <br>
            <br>
            French and Redmer (2015), Physical Review B 91, 014308</a>
            <br>
            <br>
            <br>
            <br>

            <b>Contributors:</b>
            <br><br>
            <b>Baptiste Journaux (Lead)</b> - University of Washington, Earth and Space Sciences Department, Seattle, USA
            <br><br>
            <b>J. Michael Brown</b> - University of Washington, Earth and Space Sciences Department, Seattle, USA
            <br><br>
            <b>Penny Espinoza</b> - University of Washington, Earth and Space Sciences Department, Seattle, USA
            <br><br>
            <b>Ula Jones</b> - University of Washington, Earth and Space Sciences Department, Seattle, USA
            <br><br>
            <b>Erica Clinton</b> - University of Washington, Earth and Space Sciences Department, Seattle, USA
            <br><br>
            <b>Tyler Gordon</b> - University of Washington, Department of Astronomy, Seattle, USA
            <br><br>
            <b>Matthew J. Powell-Palm</b> - Texas A&M University, Department of Mechanical Engineering, USA
            <br><br>
            <b>Jack Rosenbloom</b> - University of Washington, Paul G. Allen School of Computer Science and Engineering
        <div>
        """

        label = QLabel(reference_text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(True)  # Enable clickable links
        label.setWordWrap(True)
        more_layout.addWidget(label)

    # Opens SeaFreeze GitHub
    def open_github_page(self):
        # Define the URL to your GitHub repository
        github_url = "https://github.com/Bjournaux/SeaFreeze"
 
        # Open the URL in the default web browser
        QDesktopServices.openUrl(QUrl(github_url))

    # SAVE INDIVIDUAL FILE DATA
    def save_data(self, graphtype):
        # Get the current date and time
        current_datetime = datetime.now()
        timestamp_str = current_datetime.strftime("%d-%m-%Y %H:%M:%S")
        self.file_name = str(graphtype) + " " + self.material

        if (not graphtype == "" and not self.material == "" and self.current_Tmin and self.current_Tmax and self.current_nT
            and self.current_Pmin and self.current_Pmax and self.current_nP):
            data = {
                "Type": self.file_name,
                "date": timestamp_str,
                "version": "SF_version 1.0.1",
                "t": f"Temperature (K) {self.current_Tmin}, {self.current_Tmax}, {self.current_nT}",
                "p": f"Pressure (MPa) {self.current_Pmin}, {self.current_Pmax}, {self.current_nP}",
                "#": "##############################################################"
            }
            pts = []
            # Format each point as (x, y, z) if 3d or (x, y) if 2d
            for item in self.graphtype_to_points[graphtype]:
                if isinstance(item, tuple):
                    if len(item) == 3:
                        for point in self.graphtype_to_points[graphtype]:
                            point_str = (point[0], point[1], point[2])
                            pts.append(point_str)
                        for i, pt in enumerate(pts):
                            data[f"Point_{i + 1}"] = f"{pt[0]}, {pt[1]}, {pt[2]}"
                    elif len(item) == 2:
                        for point in self.graphtype_to_points[graphtype]:
                            point_str = (point[0], point[1])
                            pts.append(point_str)
                        for i, pt in enumerate(pts):
                            data[f"Point_{i + 1}"] = f"{pt[0]}, {pt[1]}"
            
            return data.values()
        else:
            print("Input requirements not met")
            return

    # SAVE FILE(S)
    def save_files(self):
        graphtype = self.graphtype_export_checkboxes[self.graphtype_index]
        # find which graph type buttons were selected
        for graphtype in self.graphtype_export_checkboxes:
            # add newly saved file to file list
            self.file_dict.update({graphtype + " " + self.material: self.save_data(graphtype)})
       
        # Prompt user for directory
        directory_path = QFileDialog().getExistingDirectory(None, "Select Directory",
                                                                  options=QFileDialog.Option.ShowDirsOnly)
        for file_name in self.file_dict.keys():
            if self.file_dict[file_name]:
                data = self.file_dict[file_name]
                self.df = pandas.DataFrame([data])
               
        if directory_path:
            # if a directory is found, loop through all files in dict and save each
            for file_name in self.file_dict.keys():
                file_path = f"{directory_path}/{file_name}{self.export_type}"
                self.file_paths.append(file_path)

        for path, data in zip(self.file_paths, self.file_dict.values()):
            if path.endswith(".xlsx"):
                # Save as Excel file
                print("Saving as Excel")
                excel_writer = pandas.ExcelWriter(path, engine='xlsxwriter')
                self.df.to_excel(excel_writer, sheet_name='Sheet1', index=True)
                excel_writer._save()
                print("Saved as Excel")
            elif path.endswith(".txt"):
                # Save as Text file
                print("Saving as Text")
                with open(path, "w") as txt_file:
                    if data:
                        for value in data:
                            txt_file.write(f"{value}\n")
                print("Saved as Text")
            elif path.endswith(".json"):
                # Save as JSON file
                print("Saving as JSON")
                with open(path, "w") as json_file:
                    # Convert dict_values to a list
                    json.dump(list(value for value in data), json_file, indent=4)
                print("Saved as JSON")
            else: return
            self.graphtype_index += 1
        self.graphtype_index = 0

# Create and show the main window after the splash screen is closed
def show_main_window(window):
    window.show()

# Displays splash before loading the main window
def show_splash_screen():
    app = QApplication(sys.argv)

    # Load the image for the splash screen
    splash_pix = QPixmap("SeaFreeze_Pic.png")
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    # Scale the image to desired size (e.g., 50% of the original size)
    scaled_pix = splash_pix.scaled(splash_pix.width() // 2, splash_pix.height() // 2,
                                   Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    # Create the splash screen with the scaled image
    splash = QSplashScreen(scaled_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.setMask(scaled_pix.mask())
    splash.show()

    window = GraphWindow()
    # Schedule to close the splash screen and show the main window
    QTimer.singleShot(1000, lambda: [splash.close(), show_main_window(window)])

    # Exit the app when the main window is closed
    sys.exit(app.exec())

if __name__ == "__main__":
    show_splash_screen()