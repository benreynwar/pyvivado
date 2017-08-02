library ieee;
use ieee.std_logic_1164.all;

entity TestE is
  port (
    i: in std_logic;
    o: out std_logic
    );
end TestE;

architecture arch of TestE is
begin
  o <= i;
end arch;
