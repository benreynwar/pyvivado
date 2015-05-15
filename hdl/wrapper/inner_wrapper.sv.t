// -*- verilog -*- 

import pyvivado_utils::*;

module InsideDutWrapper
  ({% for signal in signals_in %}
    input logic [{{signal.width}}-1: 0] idw_slv_{{signal.name}},{% endfor %}{% for signal in signals_out %}
    output logic [{{signal.width}}-1: 0] idw_slv_{{signal.name}},{% endfor %}{% for signal in port_signals %}
    input logic [{{signal.inwidth}}-1: 0] idw_slvin_{{signal.name}},
    output logic [{{signal.outwidth}}-1: 0] idw_slvout_{{signal.name}},{% endfor %}
    input logic clk
  );

  {% for signal in signals_in %}
  {{signal.sv_typ}};{% endfor %}
  {% for signal in signals_out %}
  {{signal.sv_typ}};{% endfor %}
  {% for signal in signals_in %}
  assign idw_{{signal.name}} =  {{signal.sv_from_slv}};{% endfor %}
  {% for signal in signals_out %}
  assign idw_slv_{{signal.name}} = {{signal.sv_to_slv}};{% endfor %}
  {% for signal in port_signals %}
  {{signal.name}}.connect_to_slv({{signal.direction}}, id_slvin_{{signal.name}}, id_slvout_{{signal.name}});{% endfor %}
                                    
  {{dut_name}} {% if dut_parameters %}
      #({% for name, value in dut_parameters.items() %}
      .{{name}}({{value}}) {% if not loop.last %},{% endif %}{% endfor %}
      ) dut{% endif %}
    ( {% for clock_name in clock_names %}
      .{{clock_name}}(clk),{% endfor %}{% for signal in signals_in + signals_out + port_signals%}
      .{{signal.name}}(idw_{{signal.name}}){% if not loop.last %},{% endif %} {% endfor %}
    );
endmodule
