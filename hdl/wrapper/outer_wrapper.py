import os
import logging

from pyvivado import interface, signal, config, builder, utils

logger = logging.getLogger(__name__)

class OuterWrapperBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.interface = params['interface']
        total_width_in = self.interface.total_width_in()
        end_index = total_width_in-1
        signals_in = []
        for wire_name, wire_type in self.interface.wires_in:
            start_index = end_index - wire_type.width + 1
            signal = {
                'source': 'in_data({} downto {})'.format(
                    end_index, start_index),
                'name': wire_name,
                'width': wire_type.width,
            }
            end_index = start_index - 1
            signals_in.append(signal)
        signals_out = []
        for wire_name, wire_type in self.interface.wires_out:
            signal = {
                'name': wire_name,
                'width': wire_type.width,
            }
            signals_out.append(signal)

        self.template_params = {
            'total_width_in': self.interface.total_width_in(),
            'total_width_out': self.interface.total_width_out(),
            'signals_in': signals_in,
            'signals_out': signals_out,
        }

    def get_filename(self, directory):
        return os.path.join(directory, 'outer_wrapper.vhd')

    def build(self, directory):
        template_fn = os.path.join(config.hdldir, 'wrapper', 'outer_wrapper.vhd.t')
        output_fn = self.get_filename(directory)
        utils.format_file(template_fn, output_fn, self.template_params)
        
    def required_filenames(self, directory):
        return [
            self.get_filename(directory),
        ]
