-- -*- vhdl -*- 
  
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.pyvivado_utils.all;
{% for package in packages %}
use {{package}}.all;
{% endfor %}

entity OutsideDutWrapper is
  port(
    signal in_data: in std_logic_vector({{total_width_in}}-1 downto 0);
    signal out_data: out std_logic_vector({{total_width_out}}-1 downto 0);
    signal clk: std_logic);
end OutsideDutWrapper;

architecture arch of OutsideDutWrapper is
  {% for signal in signals_in + signals_out%}
  signal odw_slv_{{signal.name}}: std_logic_vector({{signal.width}}-1 downto 0);
  {% endfor %}
begin
  {% for signal in signals_in %}
  odw_slv_{{signal.name}} <= {{signal.source}};
  {% endfor %}
  out_data <= {% for signal in signals_out %}odw_slv_{{signal.name}}{% if not loop.last %}&{% endif %}{% endfor %};
 
  dut: entity work.InsideDutWrapper
    port map(
      {% for signal in signals_in + signals_out %}
      idw_slv_{{signal.name}} => odw_slv_{{signal.name}},
      {% endfor %}
      clk => clk
    );
end arch;
 
