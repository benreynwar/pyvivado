library ieee;
use ieee.std_logic_1164.all;

entity TestE is
  port (
    i: in std_logic;
    o: out std_logic
    );
end TestE;

architecture arch of TestE is
  signal intermed: std_logic;
begin
  intermed <= not i;
  o <= not intermed;
end arch;
