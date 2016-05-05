from pyvivado.base_project import BuilderProject


class FPGAProject(BuilderProject):
    '''
    A python wrapper around a Vivado project that is designed to be deployed
    to the FPGA and communicated with over JTAG and the JTAG-to-AXI block.
    '''

    @classmethod
    def make_parent_params(
            cls, the_builder, parameters, directory,
            tasks_collection=None, part='', board=''):
        '''
        Takes the top level builder (which must have an AXI4Lite interface) along
        with the project parameters and generate the parameters required by
        `BuilderProject.create`.
        '''
        parameters['board_params'] = boards.get_board_params(board)
        if parameters['board_params']['name'] == 'profpga:uno2000':
            jtagaxi_builder = jtag_axi_wrapper_no_reset.JtagAxiWrapperNoResetBuilder(parameters)
        else:
            jtagaxi_builder = jtag_axi_wrapper.JtagAxiWrapperBuilder(parameters)
        return {
            'design_builders': [the_builder, jtagaxi_builder],
            'simulation_builders': [],
            'parameters': parameters,
            'directory': directory,
            'tasks_collection': tasks_collection,
            'part': part,
            'board': board,
        }

    @classmethod
    def create_or_update(
            cls, the_builder, parameters, directory,
            tasks_collection=None, part='', board=''):
        '''
        Create a new FPGAProject if one does not already exist in the 
        directory.  If one does exist and the dependencies have been modified
        then delete the old project and create a new one.  If one does exist
        and the dependencies have not been modified then use the existing
        project.

        Args: 
            `the_builder`: The builder for the top level module with an AXI4Lite
                 interface.
            `parameters`: The top level parameters for the design.  These are
                 passed the builders of any packages required. 
            `directory`: The directory where the project will be created.
            `tasks_collection`: How to keep track of the Vivado processes we start.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to used when implementing.
        '''
        parent_params = cls.make_parent_params(
            the_builder=the_builder, parameters=parameters, directory=directory,
            tasks_collection=tasks_collection, part=part, board=board)
        if os.path.exists(directory):
            cls.delete_if_changed(**parent_params)
        if os.path.exists(directory):
            logger.debug('Using old Project.')
            p = cls(directory=directory, tasks_collection=tasks_collection)
        else:
            logger.debug('Making new Project.')
            os.makedirs(directory)
            p = super().create(**parent_params)
            t = p.wait_for_most_recent_task()
            
            errors = t.get_errors()
            assert(len(errors) == 0)
        return p

    def get_monitors_hwcode(self, monitor_task):
        '''
        Get the hardware code for the FPGA that this project has been deployed to.
        '''
        max_waits = 120
        n_waits = 0
        hwcode = None
        while (hwcode is None) and (n_waits < max_waits) and (not monitor_task.is_finished()):
            hwcode = connection.get_projdir_hwcode(self.directory)
            n_waits += 1
            time.sleep(1)
        # If the task is finished something must have gone wrong
        # so log it's messages.
        if monitor_task.is_finished():
            monitor_task.log_messages(monitor_task.get_messages())
        deploy_errors = monitor_task.get_errors()
        logger.debug('Waited {}s to see deployment'.format(n_waits))
        if (len(deploy_errors) != 0):
            raise Exception('Got send_to_fpga_and_monitor errors.')
        if hwcode is None:
            raise Exception('Failed to deploy project')
        return hwcode

    def wait_for_monitor(self, hwcode, monitor_task):
        max_waits = 120
        n_waits = 0
        # Check to see that correct proj_dir is associated with the hwcode
        # and that it has been monitored recently.
        def checks_out():
            projdir_correct = (self.directory == connection.get_hwcode_projdir(hwcode))
            active = redis_utils.hwcode_A_active(hwcode)
            return projdir_correct and active
        while (not checks_out()) and (n_waits < max_waits) and (not monitor_task.is_finished()):
            n_waits += 1
            time.sleep(1)
        # If the task is finished something must have gone wrong
        # so log it's messages.
        if monitor_task.is_finished():
            monitor_task.log_messages(monitor_task.get_messages())
        deploy_errors = monitor_task.get_errors()
        logger.debug('Waited {}s to see deployment'.format(n_waits))
        if (len(deploy_errors) != 0):
            raise Exception('Got send_to_fpga_and_monitor errors.')

    def monitor_existing(self):
        '''
        Find an FPGA running this project that is not already monitored, and start
        monitoring it.

        Returns a (t, conn) tuple where:
            `t`: is the `Task` wrapping the Vivado process monitoring the FPGA, and
            `conn`: is the `Connection` with which this python process can
                 communicate the monitor.
        '''
        hwcode = redis_utils.get_unmonitored_projdir_hwcode(self.directory)
        if hwcode is None:
            raise Exception('No free hardware running this project found.')
        hwtarget, jtagfreq = config.hwtargets[hwcode]
        description = 'Monitor Redis connection and pass command to FPGA.'
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::monitor_redis {} {} {:0} 0'.format(hwcode, hwtarget, int(jtagfreq)),
            description=description,
            tasks_collection=self.tasks_collection,
        )
        t.run()
        self.wait_for_monitor(hwcode=hwcode, monitor_task=t)
        conn = connection.Connection(hwcode)
        return t, conn


    def send_to_fpga_and_monitor(self, fake=False):
        '''
        Send the bitstream of this project to an FPGA and start
        monitoring that FPGA.

        Returns a (t, conn) tuple where:
            `t`: is the `Task` wrapping the Vivado process monitoring the FPGA, and
            `conn`: is the `Connection` with which this python process can
                 communicate the monitor.
        '''
        if fake:
            # First kill any monitors connected to this project.
            connection.kill_free_monitors(self.directory)
            fake_int = 1
            description = 'Faking sending the project to fpga and monitoring.'
        else:
            fake_int = 0
            description = 'Sending project to fpga and monitoring.'
        # Get the hardware code for an unmonitored FPGA.
        self.params = self.read_params()
        hwcode = redis_utils.get_free_hwcode(self.params['board_params']['name'])
        if hwcode is None:
            raise Exception('No free hardware found.')
        hwtarget, jtagfreq = config.hwtargets[hwcode]
        logger.info('Using hardware: {}'.format(hwcode))
        # Spawn a Vivado process to deploy the bitstream and
        # start monitoring.
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::send_to_fpga_and_monitor {{{}}} {} {} {} {}'.format(
                self.directory, hwcode, hwtarget, int(jtagfreq), fake_int),
            description=description,
            tasks_collection=self.tasks_collection,
        )
        t.run()
        # Wait for the task to start monitoring and get the
        # hardware code of the free fpga.
        self.wait_for_monitor(hwcode=hwcode, monitor_task=t)
        # Create a Connection object for communication with the FPGA/
        conn = connection.Connection(hwcode)
        return t, conn
