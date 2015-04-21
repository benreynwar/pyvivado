-- -*- vhdl -*- 
  
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.pyvivado_utils.all;
{% for package in packages %}
use {{package}}.all;
{% endfor %}

entity DummyDutWrapper is
  port(
{% for clock_name in clock_names %}
    signal {{clock_name}}: in std_logic;
{% endfor %}
    {% for signal in signals_in + signals_out%}
    {% if signal.direction =="in" %}
    signal {{signal.name}}: in {{signal.typ}}{% if not loop.last %};{% endif %} 
    {% else %}
    signal {{signal.name}}: out {{signal.typ}}{% if not loop.last %};{% endif %} 
    {% endif %}
    {% endfor %}
  );
end DummyDutWrapper;
 
architecture arch of DummyDutWrapper is
begin
  dut: entity work.{{wrapped_module_name}}
    {% if dut_parameters %}
    generic map(
      {% for name, value in dut_parameters.items() %}
      {{name}} => {{value}} {% if not loop.last %},{% endif %}
      {% endfor %}
      )
    {% endif %}
    port map(
      {% for clock_name in clock_names %}
      {{clock_name}} => {{clock_name}},
      {% endfor %}
      {% for signal in signals_in + signals_out %}
      {{signal.name}} => {{signal.name}}{% if not loop.last %},{% endif %} 
      {% endfor %}
    );
end arch;
