from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileDialog, QPushButton, QLabel, QGroupBox, QWidget, QHBoxLayout, QScrollArea, \
    QMessageBox, QInputDialog

import sys
import random

from jinja2 import Environment, FileSystemLoader

from gui_client1 import Session
import os
import json
import time
import subprocess
import string
import datetime


class Worker_local(QRunnable):
    '''
    Worker thread for local running
    '''

    # def __init__(self, session_ssh, files, output, widget
    def __init__(self, session_ssh, queue_label):
        super(Worker_local, self).__init__()
        self.session = session_ssh
        self.queue = {}
        self.queue_label = queue_label

    @pyqtSlot()
    def run(self):
        '''
        Queue function
        '''
        while True:
            time.sleep(1)
            self.update_label_queue()
            if self.queue:
                jobs_this_itteration = []
                queue_copy = dict.copy(self.queue)
                for job in queue_copy:
                    jobs_this_itteration.append(job)
                    self.process_job(job_id=job, data=queue_copy[job])

                for job in jobs_this_itteration:
                    self.queue.pop(job)

    def add_job(self, job_id, data):
        self.queue[job_id] = data

    def update_label_queue(self):
        self.queue_label.setText(str(len(self.queue)))

    def process_job(self, job_id, data):
        job_id = job_id
        output = data["output"]
        filenames = data["filenames"]
        widget_obj = data["widget"]
        mode = data["mode"]
        jobname = data["jobname"]
        tools = data["tools"]

        # Select GUI compontents
        groupbox = widget_obj.findChild(QScrollArea).findChild(QGroupBox, job_id)
        file_status_label = widget_obj.findChild(QScrollArea).findChild(QGroupBox, job_id).findChild(QLabel,
                                                                                                     "file_status")
        save_button = widget_obj.findChild(QScrollArea).findChild(QGroupBox, job_id).findChild(QPushButton, "save_file")
        log_button = widget_obj.findChild(QScrollArea).findChild(QGroupBox, job_id).findChild(QPushButton, "get_error")
        current_job_nr = widget_obj.findChild(QLabel, "label_active_jobs_nr")
        failed_job = widget_obj.findChild(QLabel, "label_failed_nr")

        # file_status
        file_status_label.setText("In progress...")

        # Process file here
        if mode:
            # Run tool local
            run_args = ['python3'] + [tools["Pipeline script"]]
            result = subprocess.run(run_args, capture_output=True)

            stdout, stderr = result.stdout, result.stderr
            groupbox.stdout = stdout.decode("utf-8")
            groupbox.stderr = stderr.decode("utf-8")

        else:
            # Run tool trough ssh
            stdin, stdout, stderr = self.session.client.exec_command(f"{tools['Pipeline script']}")
            exit_status = stdout.channel.recv_exit_status()
            print('done ', exit_status)

            groupbox.stdout = stdout.read().decode("utf-8")
            groupbox.stderr = stderr.read().decode("utf-8")
            print("stderr", groupbox.stderr, bool(groupbox.stderr))
        groupbox.run_output = output
        groupbox.run_mode = mode
        groupbox.job_id = job_id
        groupbox.output = data["output"]
        groupbox.filenames = data["filenames"]
        groupbox.widget_obj = data["widget"]
        groupbox.mode = data["mode"]
        groupbox.jobname = data["jobname"]
        groupbox.tools = data["tools"]
        data["stderr"] = groupbox.stderr
        data["stdout"] = groupbox.stdout
        groupbox.data = data
        if not groupbox.stderr:

            file_status_label.setText("Finished successfully")
            save_button.setHidden(False)
        else:
            failed_job.setText(str(int(failed_job.text()) + 1))
            file_status_label.setText("Failed")
        log_button.setHidden(False)


class LogWindow(QtWidgets.QDialog):
    def __init__(self):
        super(LogWindow, self).__init__()
        uic.loadUi("ui_views/logwindow.ui", self)

    def generate_log(self, data):
        self.label_filename.setText(data['jobname'])
        env = Environment(loader=FileSystemLoader("ui_views/resources"))
        template = env.get_template('log_template.html')
        output_from_parsed_template = template.render(data=data, timestamp=datetime.datetime.now().strftime("%d-%B-%y at %T"))
        print(output_from_parsed_template)
        data = [output_from_parsed_template]
        # data.append(f"""<html><head/><body><p><span style=" font-size:18pt; font-weight:600;">Job: </span>(<span style=" font-size:18pt;">{jobname}</span></p><p><span style=" font-size:14pt; font-weight:600;">Job id: </span><span style=" font-size:14pt;">{job_id}</span></p><p><span style=" font-size:14pt; font-weight:600;">Log generated at:</span> {datetime.datetime.now().isoformat()}</p><p><br/></p><p><br/></p><p><br/></p><p><br/></p><p><br/></p><p/>""")
        # data.append(f"<span style='font-size:18pt; font-weight:600;'>{jobname}</span>")
        # data.append(f'')
        # data.append(f"Jobname: {jobname} with jobID: {job_id}")
        # data.append(f"Generated at {datetime.datetime.now().isoformat()}")
        # data.append(f"Mode: {'local' if mode else 'ssh'}")
        # data.append(f"\n\nUsed files:\n" + "\n".join(f'{os.path.basename(x)}' for x in files))
        # data.append(f"\nTools used from:\n" + "\n".join(f'{x}: {tools[x]}' for x in tools))
        # data.append(f"\nOutput can be found at: {output}")
        # data.append(f"\nStdout: \n{stdout}")
        # data.append(f"\nStderr: \n{stderr}")
        # data.append(f"</body></html>")
        return data

    def print_to_browser(self, data):
        for line in data:
            self.textBrowser.append(line)
        self.exec()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()  # Call the inherited classes __init__ method
        uic.loadUi("ui_views/mainwindow.ui", self)

        # Default values:
        self.mode_isLocal = False
        self.session = Session()
        self.file_list = []

        self.active_jobs = 0
        self.current_jobs = 0
        self.failed_jobs = 0

        # Start subprocess
        self.threadpool = QThreadPool()
        self.worker = Worker_local(session_ssh=self.session, queue_label=self.label_active_jobs_nr)
        self.threadpool.start(self.worker)
        # Load defaults:
        self.set_default_ssh()
        self.set_default_tools()
        self.set_default_run()

        # Init buttons navigation
        self.update_mode()
        self.radioButton_mode_local.toggled.connect(self.update_mode)
        self.radioButton_mode_ssh.toggled.connect(self.update_mode)

        self.pushButton_nav_ssh.clicked.connect(lambda: self.change_view(0))
        self.pushButton_nav_tools.clicked.connect(lambda: self.change_view(1))
        self.pushButton_nav_run.clicked.connect(lambda: self.change_view(2))

        self.pushButton_nav_jobs.clicked.connect(lambda: self.change_view(4))

        # Init SSH buttons
        self.pushButton_connect.clicked.connect(self.ssh_connect)
        self.pushButton_drop_connection.clicked.connect(self.ssh_disconnect)
        self.pushButton_saveconnection.clicked.connect(lambda: set_default(path="saved_data/default_ssh.json",
                                                                           data=self.get_fields_ssh(
                                                                               self.checkBox_save_password.isChecked())))
        self.pushButton_save_paths.clicked.connect(
            lambda: set_default(path=f"saved_data/default_tools_{'local' if self.mode_isLocal else 'ssh'}.json",
                                data=self.get_fields_tools()))

        # Run buttons
        self.pushButton_addfiles.clicked.connect(self.get_files)
        self.pushButton_save_output.clicked.connect(
            lambda: set_default(path=f"saved_data/default_run_{'local' if self.mode_isLocal else 'ssh'}.json",
                                data=self.get_fields_run()))
        self.pushButton_run_pipeline.clicked.connect(self.run_pipe)

        # SSH file selection
        self.pushButton_search_path.clicked.connect(self.ssh_file_selector)
        self.pushButton_ssh_file_continue.clicked.connect(self.populate_main_file)

        self.show()

    def update_mode(self):
        """Set mode to local or ssh"""
        if self.radioButton_mode_local.isChecked() and not self.radioButton_mode_ssh.isChecked():
            self.mode_isLocal = True
            self.set_default_run()
            self.set_default_tools()
            return True
        else:
            self.mode_isLocal = False
            self.set_default_run()
            self.set_default_tools()
            return False

    def change_view(self, index):
        """Change view of the stackedWidget"""
        self.stackedWidget_pages.setCurrentIndex(index)

    def get_files(self):
        """Get (fasta) files"""
        files = None
        self.update_mode()
        if self.mode_isLocal:
            files = self.openFileNamesDialog()

        else:
            self.clear_files_ssh()
            files = self.get_files_ssh()

        if files:
            for file in files:
                self.file_list.append(file)
                self._populate_file_list(file)

    def openFileNamesDialog(self, defaultdir="/"):
        """Opens a filenames dialog"""
        files, _ = QFileDialog.getOpenFileNames(None, 'Open file(s)', defaultdir,
                                                "Fasta file (*.fasta *.fastq);;all files(*.*)")
        if files:
            return files
        return None

    def get_files_ssh(self):
        """Checks if there is an active session and then changes view to index for ssh files"""
        if self.session.isActive:
            self.stackedWidget_pages.setCurrentIndex(3)
        else:
            create_message_box(msg_type="warning", text="No active SSH connection",
                               informative="Connect to ssh trough 'SSH Setup'")

    def populate_main_file(self):
        """Creates label + button for every file"""
        for file in self.file_list:
            self._populate_file_list(file)
        self.change_view(2)

    def get_fields_ssh(self, password=True):
        """
        Gets all values from the lineEdit classes from ssh page.
        :param password: if False, changes string with password to empty string
        :return: data as dict
        """
        field_values = {self.label_hostname.text(): self.lineEdit_host.text(),
                        self.label_username.text(): self.lineEdit_username.text(),
                        self.label_port.text(): self.lineEdit_port.text(),
                        self.label_publickey.text(): self.lineEdit_publickey.text() if self.lineEdit_publickey.text() else None,
                        self.label_password.text(): self.lineEdit_password.text() if password else ''}
        return field_values

    def get_fields_tools(self):
        """
        Gets all values from the lineEdit classes from tools page.
        :return: data as dict
        """
        data = {self.label_pipeline_script_path.text(): self.lineEdit_pipeline_script_path.text(),
                self.label_trimgalore.text(): self.lineEdit_trimgalore_path.text(),
                self.label_cutadapt_path.text(): self.lineEdit_cutadapt_path.text(),
                self.label_minimap_path.text(): self.lineEdit_minimap_path.text(),
                self.label_fastqc_path.text(): self.lineEdit_fastqc_path.text(),
                self.label_featurecount.text(): self.lineEdit_feature_path.text(),
                self.label_multiqc.text(): self.lineEdit_multiqc_path.text()}
        return data

    def get_fields_run(self):
        """
        Gets all values from the lineEdit classes from run page.
        :return: data as dict
        """
        data = {self.label_threads.text(): self.spinBox_threads.value(),
                self.label_skip.text(): self.checkBox_skip_files.isChecked(),
                self.label_pipeline_output_path.text(): self.lineEdit_pipeline_output.text()}
        return data

    def ssh_connect(self):
        """
        Sets up a ssh connection
        """
        fields = self.get_fields_ssh()
        try:
            self.session.client.load_system_host_keys()
            self.session.client.connect(hostname=fields[self.label_hostname.text()],
                                        username=fields[self.label_username.text()],
                                        port=fields[self.label_port.text()],
                                        password=fields[self.label_password.text()])
            self.session.isActive = True
            informative = '\n'.join([f"{x}: {fields[x]}" if x != "Password" else '' for x in fields])
            self.ssh_connection_label_update()
            create_message_box(text="Connection established!", informative=f"Connected to:\n{informative}")
        except Exception as e:
            print(f"Error: {e}")
            self.ssh_connection_label_update()
            create_message_box(msg_type='critical', text=str(e), informative=f"Please check your provided parameters.")

    def ssh_disconnect(self, message=True):
        """
        Disconnects the connection to ssh
        """
        self.session.client.close()
        self.session.isActive = False
        self.ssh_connection_label_update()
        if message:
            create_message_box(text="Connection closed!")

    def set_default_ssh(self):
        """Changes the text in ssh page to saved strings"""
        data = load_default("saved_data/default_ssh.json")
        if data:
            self.lineEdit_host.setText(data[self.label_hostname.text()])
            self.lineEdit_username.setText(data[self.label_username.text()])
            self.lineEdit_password.setText(data[self.label_password.text()])
            self.lineEdit_publickey.setText(data[self.label_publickey.text()])
            self.lineEdit_port.setText(data[self.label_port.text()])

    def set_default_tools(self):
        """Changes the text in tools page to saved strings"""
        if self.mode_isLocal:
            data = load_default("saved_data/default_tools_local.json")
        else:
            data = load_default("saved_data/default_tools_ssh.json")
        if data:
            self.lineEdit_pipeline_script_path.setText(data[self.label_pipeline_script_path.text()])
            self.lineEdit_trimgalore_path.setText(data[self.label_trimgalore.text()])
            self.lineEdit_cutadapt_path.setText(data[self.label_cutadapt_path.text()])
            self.lineEdit_minimap_path.setText(data[self.label_minimap_path.text()])
            self.lineEdit_fastqc_path.setText(data[self.label_fastqc_path.text()])
            self.lineEdit_feature_path.setText(data[self.label_featurecount.text()])
            self.lineEdit_multiqc_path.setText(data[self.label_multiqc.text()])

    def set_default_run(self):
        """Changes the text in run page to saved strings"""
        if self.mode_isLocal:
            data = load_default("saved_data/default_run_local.json")
        else:
            data = load_default("saved_data/default_run_ssh.json")
        if data:
            self.spinBox_threads.setValue(data[self.label_threads.text()])
            self.checkBox_skip_files.setChecked(bool(self.label_skip.text()))
            self.lineEdit_pipeline_output.setText(data[self.label_pipeline_output_path.text()])

    def ssh_connection_label_update(self):
        """Updates the connection_label to the correct string"""
        if self.session.isActive:
            self.label_ssh_connection.setText("SSH: Connected")
            self.label_ssh_connection.setStyleSheet("background-color: lightgreen")
        else:
            self.label_ssh_connection.setText("SSH: No Connection")
            self.label_ssh_connection.setStyleSheet("background-color: red")

    def ssh_file_selector(self):
        """Function that handles the file selection if SSH protocol is used"""
        path = self.lineEdit_file_path_ssh.text()
        filenames_filtered = []
        if path:
            filenames = self.session.probe_dir(path)

            if filenames:
                for name in filenames:
                    if name.endswith(".fastq") or name.endswith(".fastq.gz"):
                        filenames_filtered.append(name)

            if filenames_filtered:
                filenames_filtered = [os.path.join(path, x) for x in filenames_filtered]
                self._populate_file_ssh_left(files=filenames_filtered)
            else:
                found = "Files / folders found:\n"
                if type(filenames) == list:
                    found += "\n".join(filenames)
                elif type(filenames) == str:
                    found += filenames

                create_message_box(msg_type="critical", text="Could not find any (supported) files in provided path",
                                   informative="fastq and fastq.gz are only supported", details=found)
        else:
            create_message_box(msg_type="warning", text="Path can't be empty")

    # Populate file list. Underlying functions create new widgets.
    def _populate_file_list(self, file):
        """Creates individual file objects in the files widgets on the run page"""
        filename = file.split("/")[-1]
        file_label = QLabel(filename)
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon('ui_views/resources/delete.png'))
        delete_btn.setMinimumWidth(20)
        delete_btn.setMaximumWidth(20)
        delete_btn.setFlat(True)
        delete_btn.setObjectName(file)
        delete_btn.clicked.connect(lambda: self.delete_file(self.sender()))
        file_box = QGroupBox()
        file_box.setObjectName(file)
        file_box.setMaximumHeight(25)
        layout_file_box = QHBoxLayout(file_box)
        layout_file_box.addWidget(file_label)
        layout_file_box.addWidget(delete_btn)
        layout_file_box.setContentsMargins(0, 0, 0, 0)
        group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        group.setObjectName(file)
        group.setLayout(layout_file_box)
        self.verticalLayout_files.addWidget(group)
        self.label_files.setHidden(True)

    def _populate_file_ssh_left(self, files):
        """Creates individual file objects in the left column on the SSH file selector page"""
        for file in files:
            filename = file.split("/")[-1]
            file_label = QLabel(filename)
            move_btn = QPushButton()
            move_btn.setIcon(QIcon('ui_views/resources/arrow_right.svg'))
            move_btn.setMinimumWidth(20)
            move_btn.setMaximumWidth(20)
            move_btn.setFlat(True)
            move_btn.setObjectName(file)
            move_btn.clicked.connect(lambda: self._populate_file_ssh_right(self.sender()))
            file_box = QGroupBox()
            file_box.setObjectName(file)
            layout_file_box = QHBoxLayout(file_box)
            layout_file_box.addWidget(file_label)
            layout_file_box.addWidget(move_btn)
            group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_left)
            group.setObjectName(file)
            group.setLayout(layout_file_box)
            self.verticalLayout_left_ssh.addWidget(group)
            self.label_ssh_left.setHidden(True)

    def _populate_file_ssh_right(self, sender):
        """Creates individual file objects in the right column on the SSH file selector page"""
        self.delete_file(sender)
        sender.parent().setHidden(True)
        sender.parent().deleteLater()
        file = sender.objectName()
        filename = file.split("/")[-1]
        file_label = QLabel(filename)
        move_btn = QPushButton()
        move_btn.setIcon(QIcon('ui_views/resources/delete.png'))
        move_btn.setMinimumWidth(20)
        move_btn.setMaximumWidth(20)
        move_btn.setFlat(True)
        move_btn.setObjectName(file)
        move_btn.clicked.connect(lambda: self.delete_file(self.sender()))
        file_box = QGroupBox()
        file_box.setObjectName(file)
        layout_file_box = QHBoxLayout(file_box)
        layout_file_box.addWidget(file_label)
        layout_file_box.addWidget(move_btn)
        group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_right)
        group.setObjectName(file)
        group.setLayout(layout_file_box)
        self.verticalLayout_ssh_right.addWidget(group)
        self.label_ssh_right.setHidden(True)
        self.file_list.append(file)

    def delete_file(self, sender):
        """Remove file from list"""
        sender.parent().setHidden(True)
        sender.parent().deleteLater()
        try:
            self.file_list.remove(sender.parent().objectName())
        except ValueError:
            pass
        if not sender.parent().parent().findChildren(QGroupBox):
            sender.parent().parent().findChild(QLabel).setHidden(False)

    def clear_files_ssh(self):
        """Deletes all labels + buttons for filenames"""
        data = self.findChild(QWidget, 'scrollAreaWidgetContents_right').findChildren(QGroupBox)
        data += self.findChild(QWidget, 'scrollAreaWidgetContents_left').findChildren(QGroupBox)
        if data:
            for file in data:
                file.deleteLater()

                file.parent().findChild(QLabel).setHidden(False)

    def _generate_job_id(self):
        pool = string.ascii_uppercase + string.digits
        return "".join(random.sample(pool, 20))

    def gettext(self):
        text, ok = QInputDialog.getText(self, 'Job name', 'Enter a job name:')
        if ok:
            if text == "":
                create_message_box(msg_type="warning", text="Job name not allowed to be empty")
                return None
            else:
                return text
        else:
            return None

    def run_pipe(self):
        files = self.file_list
        output = self.lineEdit_pipeline_output.text()
        job_id = self._generate_job_id()
        jobname = self.gettext()

        # Check if all prerequisites are fulfilled
        if not jobname or not files or not output:
            ready = False
        else:
            ready = True

        if ready:
            self.create_job_widget(jobname=jobname, job_id=job_id)
            self.label_files_jobs.setHidden(True)
            self.change_view(4)
            widget = self.findChild(QGroupBox, 'groupBox_jobs')
            self.add_job(job_id=job_id, jobname=jobname, output=output, filenames=files, widget=widget,
                         mode=self.mode_isLocal, tools=self.get_fields_tools())
        else:
            create_message_box(msg_type="warning", text="Can't start job!",
                               informative="not all prerequisistes are fullfilled. Check details for more info.",
                               details=f"Jobname provided: {bool(jobname)}\nOutput provided: {bool(output)}\nFiles "
                                       f"provided: {bool(files)}")

    def add_job(self, job_id, jobname, output, filenames, widget, mode, tools):
        data = {"output": output, "filenames": filenames, "widget": widget, "mode": mode, "jobname": jobname,
                "job_id": job_id, "tools": tools}
        self.worker.add_job(job_id=job_id, data=data)

    def create_job_widget(self, jobname, job_id):
        # Create label
        file_label = QLabel(f"Name: {jobname}")
        file_label_status = QLabel("In queue...")
        file_label_status.setObjectName("file_status")
        file_label_status.setMaximumHeight(25)

        # Create button get file
        btn_get_file = QPushButton("Save file")
        btn_get_file.setObjectName("save_file")
        btn_get_file.setHidden(True)
        btn_get_file.clicked.connect(lambda: self.save_finished_file(self.sender()))

        # Create button get log
        btn_log = QPushButton("Get log")
        btn_log.setObjectName("get_error")
        btn_log.setMaximumWidth(100)
        btn_log.setHidden(True)
        btn_log.clicked.connect(lambda: self.open_log_dialog(self.sender()))

        # Create groupbox
        file_box = QGroupBox()
        file_box.setObjectName(job_id)
        file_box.setMaximumHeight(25)

        # Extra data
        file_box.stderr = None
        file_box.stdout = None
        file_box.run_output = None
        file_box.run_pdf_location = None
        file_box.run_mode = None

        # Add widgets
        layout_file_box = QHBoxLayout(file_box)
        layout_file_box.addWidget(file_label)
        layout_file_box.addWidget(file_label_status)
        layout_file_box.addWidget(btn_get_file)
        layout_file_box.addWidget(btn_log)

        # Set margins
        layout_file_box.setContentsMargins(0, 0, 0, 0)

        # Create Qgroupbox
        group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents_2)
        group.setObjectName(job_id)
        group.setLayout(layout_file_box)
        group.log = LogWindow()
        self.verticalLayout_jobs.addWidget(group)

    def saveFileDialog(self, filename="output.pdf"):
        defaultdir = f"/{filename}"
        files, _ = QFileDialog.getSaveFileName(None, 'Save file', defaultdir,
                                               "PDF file(*.pdf);;all files(*.*)")
        if files:
            return files
        return None

    def save_finished_file(self, sender):
        print(f"Downloading file: {sender.parent().objectName()}")
        groupbox = sender.parent()
        fullpath = sender.parent().objectName()
        basename = os.path.basename(fullpath)
        save_location = self.saveFileDialog(filename=basename)
        print(f"Saving at: {save_location}")
        print(f"data: {self.sender().parent().file_data}")
        print(f"Output: {groupbox.run_output}")
        print(f"Run mode {groupbox.run_mode}")

    def open_log_dialog(self, sender):
        fullpath = sender.parent().objectName()
        basename = os.path.basename(fullpath)
        stdout = sender.parent().stdout
        error = sender.parent().stderr
        # log = sender.parent().log
        groupbox = sender.parent()
        # groupbox.run_output
        # groupbox.run_mode
        # groupbox.job_id
        # groupbox.output
        # groupbox.filenames
        # groupbox.widget_obj
        # groupbox.mode
        # groupbox.jobname
        # groupbox.tools
        log = sender.parent().log
        # stderr = error, stdout = stdout, jobname = groupbox.jobname, files = groupbox.filenames, tools = groupbox.tools, mode = groupbox.mode, output = groupbox.output, job_id = groupbox.job_id
        data = log.generate_log(groupbox.data)
        log.print_to_browser(data)


        # self.setHidden(True)
        # print(f"stdout: {stdout}")
        # print(f"sterr: {error}")


def set_default(path, data):
    """
    Creates a json file with name according to provided path
    :param path: filename
    :param data: data containing the values of the individual editLine objects
    :return: nothing
    """
    create_message_box(text="Set default",
                       informative="\n".join([f"{x}:\t{data[x] if x != 'password' else ''}" for x in data]))
    with open(path, "w") as stream:
        stream.write(json.dumps(data, indent=4))


def load_default(path):
    """
    Opens json file and returns as dicts
    :param path: path of json file
    :return: dictionary
    """
    if os.path.exists(path):
        with open(path, "r") as stream:
            data = json.load(stream)
        return data


def create_message_box(text="no text provided", informative=None, title="popup", details=None, msg_type="info"):
    """
    Creates and shows a popup notification
    :param text: primary text
    :param informative: extra information
    :param title: title of the popup
    :param details: extra details
    :param msg_type: str that determens the displayed icon
    :return: noting
    """
    msg = QMessageBox()
    icon = {"info": QMessageBox.Information,
            "warning": QMessageBox.Warning,
            "critical": QMessageBox.Critical,
            "question": QMessageBox.Question}
    msg.setIcon(icon[msg_type])
    msg.setWindowTitle(title)
    msg.setText(text)
    if informative:
        msg.setInformativeText(informative)
    if details:
        msg.setDetailedText(details)
    msg.exec()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)  # Create an instance of QtWidgets.QApplication
    main_window = MainWindow()  # Create an instance of our class
    # login_window = LoginWindow()
    app.exec_()  # Start the application