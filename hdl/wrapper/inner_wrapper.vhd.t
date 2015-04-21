-- -*- vhdl -*- 
  
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.pyvivado_utils.all;
{% for package in packages %}
use {{package}}.all;
{% endfor %}

entity InsideDutWrapper is
  port(
    {% for signal in signals_in %}
    signal idw_slv_{{signal.name}}: in std_logic_vector({{signal.width}}-1 downto 0);
    {% endfor %}
    {% for signal in signals_out %}
    signal idw_slv_{{signal.name}}: out std_logic_vector({{signal.width}}-1 downto 0);
    {% endfor %}
    signal clk: std_logic
  );
end InsideDutWrapper;
 
architecture arch of InsideDutWrapper is
  {% for signal in signals_in %}
  signal idw_{{signal.name}}: {{signal.typ}};
  {% endfor %}
  {% for signal in signals_out %}
  signal idw_{{signal.name}}: {{signal.typ}};
  {% endfor %}
begin
  {% for signal in signals_in %}
  idw_{{signal.name}} <=  {{signal.from_slv}};
  {% endfor %}
  {% for signal in signals_out %}
  idw_slv_{{signal.name}} <= {{signal.to_slv}};
  {% endfor %}
  dut: entity work.{{dut_name}}
    {% if dut_parameters %}
    generic map(
      {% for name, value in dut_parameters.items() %}
      {{name}} => {{value}} {% if not loop.last %},{% endif %}
      {% endfor %}
      )
    {% endif %}
    port map(
      {% for clock_name in clock_names %}
      {{clock_name}} => clk,
      {% endfor %}
      {% for signal in signals_in + signals_out %}
        {% if signal.direction == 'in' %}
      {{signal.name}} => idw_{{signal.name}}{% if not loop.last %},{% endif %} 
        {% else %}
      {{signal.name}} => idw_{{signal.name}}{% if not loop.last %},{% endif %}
        {% endif %}
      {% endfor %}
    );
end arch;
