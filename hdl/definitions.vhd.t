library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package {{package_name}} is
  
{% for definition in definitions %}
{{definition}}
{% endfor %}
  
end package;

package body {{package_name}} is

{% for implementation in implementations %}
{{implementation}}
{% endfor %}

end package body;
