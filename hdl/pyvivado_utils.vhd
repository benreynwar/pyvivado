library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package pyvivado_utils is
  
  function logceil(v: integer) return integer;
  function std_logic_to_slv(input: std_logic) return std_logic_vector;
  function get_index_of_first_one(slv: std_logic_vector) return integer;
  function or_slv(slv: std_logic_vector) return std_logic;
  function and_slv(slv: std_logic_vector) return std_logic;
  -- Add when required due to ambiguousness caused by array of std_logic_vector.
  function concat(slv1: std_logic_vector; slv2: std_logic_vector) return std_logic_vector;
  
end package;

package body pyvivado_utils is

  function concat(slv1: std_logic_vector; slv2: std_logic_vector) return std_logic_vector is
    variable output: std_logic_vector(slv1'length + slv2'length -1 downto 0);
  begin
    output(slv1'length+slv2'length-1 downto slv2'length) := slv1;
    output(slv2'length-1 downto 0) := slv2;
    return output;
  end;

  function std_logic_to_slv(input: std_logic) return std_logic_vector is
    variable output: std_logic_vector(0 downto 0);
  begin
    output(0) := input;
    return output;
  end;

  function logceil(v: integer) return integer is
  begin
    if (v = 0) then
      return 0;
    elsif (v = 1) then
      return 1;
    else
      return integer(ceil(log2(real(v))));
    end if;
  end function;

  function get_index_of_first_one(slv: std_logic_vector) return integer is
    variable counter: integer range 0 to slv'LENGTH;
  begin
    for counter in 0 to slv'LENGTH-1 loop
      if (slv(counter) = '1') then
        return counter;
      end if;
    end loop;
    return slv'LENGTH;
  end function;

  function or_slv(slv:std_logic_vector) return std_logic is
    variable ii: integer range slv'LOW to slv'HIGH;
    variable output: std_logic := '0';
  begin
    for ii in slv'LOW to slv'HIGH loop
      output := output or slv(ii);
    end loop;
    return output;
  end function;

  function and_slv(slv:std_logic_vector) return std_logic is
  begin
    return not or_slv(not slv);
  end function;

end package body;
