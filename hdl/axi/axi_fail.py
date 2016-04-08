import os
import logging

from pyvivado import builder, config

from pyvivado import axi

logger = logging.getLogger(__name__)


class AxiFailBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'axi', 'axi_fail.vhd'),
        ]
        self.packages = [
            'axi_utils',
        ]


class AxiFail(object):

    def __init__(self):
        self.o = axi.make_empty_axi4lite_s2m_dict()
        self.o['bresp'] = axi.DECERR
        self.o['rresp'] = axi.DECERR
        
    def predict(self):
        outputs = {
            'o': self.o,
        }
        return outputs

    def process(self, inputs):
        outputs = self.predict()
        self.o = axi.make_empty_axi4lite_s2m_dict()
        self.o['bresp'] = axi.DECERR
        self.o['rresp'] = axi.DECERR
        if inputs['reset']:
            if inputs['i']['awvalid']:
                self.o['bvalid'] = 1
                if not inputs['i']['wvalid']:
                    raise Exception('AxiFail assume awvalid and wvalid are simulataneously asserted.')
            if inputs['i']['arvalid']:
                self.o['rvalid'] = 1
        return outputs
        
