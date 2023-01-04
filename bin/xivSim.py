from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, QLabel, QLineEdit,
                             QVBoxLayout, QHBoxLayout, QStackedLayout, QGridLayout, QComboBox, QProgressBar,
                             QRadioButton, QFrame)
from PyQt5.Qt import QSize, Qt, QIntValidator, QDoubleValidator
from PyQt5.QtGui import QPalette, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np
import sys
from xivSimModule import XIVSimThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # The number of members in a typical FFXIV raid party
        self.party_number = 8

        # window basics
        self.setWindowTitle("XIV Damage Simulator")
        self.setFixedSize(QSize(1250, 750))
        # The full set of data from the GUI that will be used in the calculations
        self.full_data = {'sims': 0, 'iterations': 0, 'fight duration': 0.0, 'players': []}
        # Pay attention to mouse
        self.setMouseTracking(True)

        # A stacked layout for stats
        self.stat_layout = QStackedLayout()
        self.stat_pages = []
        for i in range(self.party_number):
            page = QWidget()
            # Create a vertical layout
            page_layout = QVBoxLayout()
            # That contains the generic stat page on top
            temp = StatPage('grey')
            page_layout.addWidget(temp)
            # and any job-specific needs below.
            temp = JobCustom('Job', self)
            page_layout.addWidget(temp)
            page.setLayout(page_layout)

            # Add this widget to the stacked layout, and the list for easier access
            self.stat_layout.addWidget(page)
            self.stat_pages.append(page)

        # Team drop down choices
        choice_layout = QVBoxLayout()
        choice_layout.addWidget(QLabel("Player Line-up     "))
        self.choices = []
        self.active_choice = 0
        for i in range(self.party_number):
            temp = LabeledDrop(i, self)
            choice_layout.addWidget(temp)
            self.choices.append(temp)

        # Start button
        self.start_button = QPushButton("Start Sim")
        self.start_button.pressed.connect(self.collect_stats)
        self.start_button.pressed.connect(self.sim_thread)

        # Progress Bar
        self.battle_prog_bar = QProgressBar()
        self.damage_prog_bar = QProgressBar()

        # Sim basic inputs
        # Sim iteration inputs
        iter_layout = QGridLayout()
        iter_layout.addWidget(QLabel("Number of Rotational Simulations: "), 0, 0)
        self.battle_iter = QLineEdit()
        validator = QIntValidator(1, 1000000)
        self.battle_iter.setValidator(validator)
        self.battle_iter.editingFinished.connect(self.set_battle_max)
        iter_layout.addWidget(self.battle_iter, 0, 1)

        iter_layout.addWidget(QLabel("Number of Damage Sims per Rotation Sim: "), 0, 2)
        self.damage_iter = QLineEdit()
        self.damage_iter.setValidator(validator)
        self.damage_iter.editingFinished.connect(self.set_dmg_max)
        iter_layout.addWidget(self.damage_iter, 0, 3)

        iter_layout.addWidget(QLabel("Fight Duration: "), 1, 0)
        self.fight_dur = QLineEdit()
        validator = QDoubleValidator(0, 1000, 2)
        self.fight_dur.setValidator(validator)
        self.fight_dur.editingFinished.connect(self.valid_fight_dur)
        iter_layout.addWidget(self.fight_dur, 1, 1)

        iter_layout.setSpacing(10)

        # Pre-plot layout
        setup_layout = QGridLayout()
        setup_layout.addLayout(iter_layout, 0, 0, 1, -1)
        setup_layout.addLayout(choice_layout, 1, 0)
        setup_layout.addLayout(self.stat_layout, 1, 1)
        setup_layout.addWidget(self.start_button, 2, 0)
        setup_layout.addWidget(self.battle_prog_bar, 2, 1)
        setup_layout.addWidget(self.damage_prog_bar, 3, 1)
        setup_layout.setHorizontalSpacing(0)

        # Plot zone
        # Plot
        self.plot = MplCanvas(None, 10, 5)
        self.plot.axes.hist([0,1,2,3,4,10,1,20,3,40])
        # Toolbar
        self.plot_toolbar = NavigationToolbar2QT(self.plot, self)
        # Number displays
        font_size = 12
        self.statistics_display = QWidget()
        layout = QHBoxLayout()
        self.mean_display = QLabel("Mean: XXXX")
        self.mean_display.setAlignment(Qt.AlignCenter)
        font = self.mean_display.font()
        font.setPointSize(font_size)
        self.mean_display.setFont(font)
        self.std_display = QLabel("Standard Deviation: XXXX")
        self.std_display.setAlignment(Qt.AlignCenter)
        self.std_display.setFont(font)
        layout.addWidget(self.mean_display)
        layout.addWidget(self.std_display)
        self.statistics_display.setLayout(layout)
        self.statistics_display.setFixedHeight(50)
        # Collect the items
        plot_zone = QVBoxLayout()
        plot_zone.addWidget(self.plot_toolbar)
        plot_zone.addWidget(self.plot)
        plot_zone.addWidget(self.statistics_display)

        # Top-level layout
        layout = QHBoxLayout()
        layout.addLayout(setup_layout)
        layout.addLayout(plot_zone)

        # Top-level widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Highlight active choice to start
        self.choices[self.active_choice].change_color(self.choices[self.active_choice].drop_box.currentText())

    def change_frame(self, index):
        # Change the visible (foreground) stat-page
        self.stat_layout.setCurrentIndex(index)

    def collect_stats(self):
        # Check if the necessary forms are filled in, and flag unacceptable ones
        if self.battle_iter.hasAcceptableInput() is False:
            self.battle_iter.setStyleSheet('''QLineEdit {background : lightcoral;}''')
        if self.damage_iter.hasAcceptableInput() is False:
            self.damage_iter.setStyleSheet('''QLineEdit {background : lightcoral;}''')
        if self.fight_dur.hasAcceptableInput() is False:
            self.fight_dur.setStyleSheet('''QLineEdit {background : lightcoral;}''')
        # Proceed to collecting the data if forms are acceptable
        if self.battle_iter.hasAcceptableInput() & self.damage_iter.hasAcceptableInput() &\
                self.fight_dur.hasAcceptableInput():
            self.full_data['sims'] = int(self.battle_iter.text())
            self.full_data['iterations'] = int(self.damage_iter.text())
            self.full_data['fight duration'] = float(self.fight_dur.text())
            player_stats = [player.layout().itemAt(0).widget().stats for player in self.stat_pages]
            player_jobs = [player.drop_box.currentText() for player in self.choices]
            job_specifics = [player.layout().itemAt(1).widget().return_data() for player in self.stat_pages]
            self.full_data['players'] = [{'job': job, 'stats': stats, 'specifics': specifics} for job, stats, specifics
                                         in zip(player_jobs, player_stats, job_specifics)]
            print('stats collected')
            print(self.full_data)

    def sim_thread(self):
        # Only proceed if the forms have acceptable values
        if self.battle_iter.hasAcceptableInput() & self.damage_iter.hasAcceptableInput() &\
                self.fight_dur.hasAcceptableInput():
            # Opperate the sim through a thread
            self.thread = XIVSimThread(self.full_data)
            # Connect the signals for updating the progress bars
            self.thread.battle_prog.connect(self.advance_battle_prog)
            self.thread.damage_prog.connect(self.advance_damage_prog)
            # Connect the plot to receive the finished Sim data
            self.thread.result.connect(self.update_plot)
            # Start the sim
            self.thread.start()
            # Don't allow the user to hit the button while the sim is running
            self.start_button.setEnabled(False)

    def set_battle_max(self):
        # Reset the background, as this form has received an acceptable input
        self.battle_iter.setStyleSheet('''QLineEdit {background : white;}''')
        # Update the max value of the associated progress bar
        self.battle_prog_bar.setMaximum(int(self.battle_iter.text()))

    def advance_battle_prog(self, e_val):
        # Update the current value of the progress bar
        self.battle_prog_bar.setValue(e_val)

    def set_dmg_max(self):
        # Reset the background, as this form has received an acceptable input
        self.damage_iter.setStyleSheet('''QLineEdit {background : white;}''')
        # Update the max value of the associated progress bar
        self.damage_prog_bar.setMaximum(int(self.damage_iter.text()))

    def advance_damage_prog(self, e_val):
        # Update the current value of the progress bar
        self.damage_prog_bar.setValue(e_val)

    def valid_fight_dur(self):
        # Reset the background, as this form has received an acceptable input
        self.fight_dur.setStyleSheet('''QLineEdit {background : white;}''')

    def update_plot(self, result):
        # Plot the results to the plot
        # Clear the currently plotted data
        self.plot.axes.cla()
        # Plot the new data
        self.plot.axes.hist(result, bins=40)
        # Add lines for the mean and one standard deviation
        self.plot.axes.axvline(np.mean(result), color='red', label='Mean')
        self.plot.axes.axvline(np.mean(result) - np.std(result), color='red', ls='--', label='Standard Deviation')
        self.plot.axes.axvline(np.mean(result) + np.std(result), color='red', ls='--')
        # Put labels and legends
        self.plot.axes.set_xlabel('Damage Per Second (DPS)')
        self.plot.axes.set_ylabel('Count')
        self.plot.axes.set_title('Histogram of DNC DPS')
        self.plot.axes.legend()
        self.plot.draw()
        # Update the additional text information
        self.mean_display.setText(f"Mean: {np.mean(result):.3f}")
        self.std_display.setText(f"Standard Deviation: {np.std(result):.3f}")
        # Allow the user to start another simulation now
        self.start_button.setEnabled(True)


class StatPage(QWidget):
    def __init__(self, color):
        super().__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)

        self.stats = {'WD': None, 'Main Stat': None, 'Speed Stat': None, 'Crit': None, 'Dhit': None, 'Det': None}
        # limit inputs to integers up to 9999
        validator = QIntValidator(0, 9999, self)

        # Create stat inputs
        # grid layout
        grid = QGridLayout()

        row = 1
        col = 1
        # Generate the multiple stat forms
        for stat in self.stats.keys():
            if row > 8:
                col = 3
            # A label for the stat
            grid.addWidget(QLabel(f"{stat}:"), row%9, col)
            # A form to input the stat value
            temp = QLineEdit()
            # Apply validator to the form
            temp.setValidator(validator)
            temp.setPlaceholderText("Provide Stat Value")
            # Connect this form to the appropriate stat-tracker
            self.update_link(temp, stat)
            grid.addWidget(temp, (row+1)%9, col)
            row += 3

        # Add some Frame lines
        # Vertical lines
        for col in [0, 2, 4]:
            temp = QFrame()
            temp.setFrameStyle(QFrame.VLine)
            temp.setLineWidth(2)
            grid.addWidget(temp, 0, col, -1, 1)
        # Horizontal lines
        for row in [0, 3, 6, 9]:
            temp = QFrame()
            temp.setFrameStyle(QFrame.HLine)
            temp.setLineWidth(2)
            grid.addWidget(temp, row, 0, 1, -1)
        # apply the grid layout
        self.setLayout(grid)

    def update_link(self, qline, stat):
        # Link the QLineEdit widget to the appropriate stat-tracker, based on which stat it represents
        stat_list = list(self.stats.keys())
        if stat == stat_list[0]:
            qline.textChanged.connect(self.update_wd)
        elif stat == stat_list[1]:
            qline.textChanged.connect(self.update_main)
        elif stat == stat_list[2]:
            qline.textChanged.connect(self.update_spd)
        elif stat == stat_list[3]:
            qline.textChanged.connect(self.update_crit)
        elif stat == stat_list[4]:
            qline.textChanged.connect(self.update_dhit)
        elif stat == stat_list[5]:
            qline.textChanged.connect(self.update_det)

    def update_wd(self, val):
        # Accept empty values as representing the value zero
        if val is None:
            val = 0
        # Keep track of the current values in the form
        self.stats[list(self.stats.keys())[0]] = val

    def update_main(self, val):
        if val is None:
            val = 0
        self.stats[list(self.stats.keys())[1]] = val

    def update_spd(self, val):
        if val is None:
            val = 0
        self.stats[list(self.stats.keys())[2]] = val

    def update_crit(self, val):
        if val is None:
            val = 0
        self.stats[list(self.stats.keys())[3]] = val

    def update_dhit(self, val):
        if val is None:
            val = 0
        self.stats[list(self.stats.keys())[4]] = val

    def update_det(self, val):
        if val is None:
            val = 0
        self.stats[list(self.stats.keys())[5]] = val

    def change_color(self, job):
        # Change the background color based on the selected job
        color = 'grey'
        match job:
            case 'AST':
                color = 'yellow'
            case 'BLM':
                color = 'purple'
            case 'DRK':
                color = 'magenta'
            case 'DRG':
                color = 'blue'
            case 'DNC':
                color = 'pink'
            case 'PLD':
                color = 'cyan'
            case 'SAM':
                color = 'orange'
            case 'WHM':
                color = 'white'

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)


class JobCustom(QWidget):
    # A widget for the job-custom part of the stat-page
    def __init__(self, job, window):
        super().__init__()
        self.setAutoFillBackground(True)

        # Set the color
        self.change_color(job)

        # Easy call to main window and it's properties
        self.window = window

        # Create the larger vertical layout
        self.layout = QVBoxLayout()

        # Track the job
        self.job = job
        # Do all job-specific things, and set the final layout
        self.reset(job)

    def change_color(self, job):
        # Change the background color based on the selected job
        color = 'grey'
        match job:
            case 'AST':
                color = 'yellow'
            case 'BLM':
                color = 'purple'
            case 'DRK':
                color = 'magenta'
            case 'DRG':
                color = 'blue'
            case 'DNC':
                color = 'pink'
            case 'PLD':
                color = 'cyan'
            case 'SAM':
                color = 'orange'
            case 'WHM':
                color = 'white'

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)

    def reset(self, job):
        # Update to the current job
        self.job = job

        # TO-DO: Clear old layout, set new layout based on job
        clear_layout(self.layout)

        # Indicate the job (perhaps unnecessary)
        self.label = QLabel(f"{job}-Specific Zone")
        self.layout.addWidget(self.label)

        if job == 'DNC':
            # Create a partner selector
            # Label the radio button choice
            choice_label = QLabel('Choose which player to have Dance Partner:')
            self.layout.addWidget(choice_label)
            # Create a radio button selection
            self.choice = QHBoxLayout()
            for i in range(self.window.party_number):
                button = QRadioButton(str(i + 1))
                self.choice.addWidget(button)
            self.layout.addLayout(self.choice)

        if job == 'SAM':
            pass

        # Set the layout once the job-specific code is done
        self.setLayout(self.layout)

    def return_data(self):
        if self.job == 'DNC':
            # Return the partner number by checking each button until a selection if found
            for button_number in range(self.choice.layout().count()):
                if self.choice.layout().itemAt(button_number).widget().isChecked():
                    return {'partner': button_number}
            # If not found, tell the user that a partner is necessary
            print('Warning: No dance partner selected. Defaulting to player 2!!')
            return {'partner': 1}

        return {}


class LabeledDrop(QWidget):
    # A Widget that contains a label and dropdown selector
    def __init__(self, n, window):
        super().__init__()
        # Keep track of an id, to link this particular widget to a particular stat page
        self.id = n
        self.window = window
        self.setParent(window)
        # Allow the background color to be changed
        self.setAutoFillBackground(True)

        # Label which player this dropdown represents
        self.label = QLabel(f"Player {n+1}:")
        self.label.setAutoFillBackground(True)

        # Create the dropdown selector
        self.drop_box = QComboBox()
        self.drop_box.addItems(['Job', 'AST', 'BLM', 'DRK', 'DRG', 'DNC', 'PLD', 'SAM', 'WHM'])
        # Connect this dropdown to actions
        # Change the color of this and the associated page, based on job selection
        self.drop_box.currentTextChanged.connect(self.change_color)
        self.drop_box.currentTextChanged.connect(window.stat_pages[self.id].layout().itemAt(0).widget().change_color)
        self.drop_box.currentTextChanged.connect(window.stat_pages[self.id].layout().itemAt(1).widget().change_color)
        # And change the contents of the job-specific section on job selection too
        self.drop_box.currentTextChanged.connect(window.stat_pages[self.id].layout().itemAt(1).widget().reset)
        # Bring the associated stat-page to the foreground when this selector is interacted with
        self.drop_box.currentTextChanged.connect(self.make_focus)

        # Arrange the label and dropdown
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.drop_box)

        self.setLayout(self.layout)

    def change_color(self, job):
        # Change the color based on the selected job
        color = 'grey'
        match job:
            case 'AST':
                color = 'yellow'
            case 'BLM':
                color = 'purple'
            case 'DRK':
                color = 'magenta'
            case 'DRG':
                color = 'blue'
            case 'DNC':
                color = 'pink'
            case 'PLD':
                color = 'cyan'
            case 'SAM':
                color = 'orange'
            case 'WHM':
                color = 'white'

        # change previously active background back
        base_color = self.window.palette().color(QPalette.Window)
        palette = self.window.choices[self.window.active_choice].palette()
        palette.setColor(QPalette.Window, QColor(base_color))
        self.window.choices[self.window.active_choice].setPalette(palette)
        # change this background to match
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)
        # set this choice to active
        self.window.active_choice = self.id

    def make_focus(self):
        # Bring the associated stat-page into the foreground
        self.window.change_frame(self.id)

    def mouseReleaseEvent(self, *args, **kwargs):
        # Bring the "tab" into focus (by showing its color) when a particular job selector tab is clicked on
        self.change_color(self.drop_box.currentText())
        # And bring the associated stat-page to the foreground
        self.window.change_frame(self.id)


class MplCanvas(FigureCanvasQTAgg):
    # A Matplotlib canvas for plotting
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Set the figure size, which can be a passed argument
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # Set the initial labels and title
        self.axes.set_xlabel('Damage Per Second (DPS)')
        self.axes.set_ylabel('Count')
        self.axes.set_title('Histogram of DNC DPS')
        super(MplCanvas, self).__init__(fig)


def clear_layout(layout):
    if layout is not None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                clear_layout(child.layout())


if __name__ == '__main__':

    # Create a pyqt application
    app = QApplication(sys.argv)
    # Create the GUI
    window = MainWindow()
    # Display it
    window.show()

    app.exec()


