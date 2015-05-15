package pyvivado_utils;

   // Virtual Classes aren't supported for Simulation in Vivado.
   // Until this is sorted I'm not going to bother working with SystemVerilog
   // so this will lie dormant.
   
   // virtual class Logic2DHelper #(parameter int WIDTHA, parameter int WIDTHB);

   //    typedef logic [WIDTHA-1:0] typ [WIDTHB-1:0];
      
   //   static function logic[WIDTHA*WIDTHB-1: 0] to_logic(ref typ twoD);
   //      logic[WIDTHA*WIDTHB-1:0] oneD;
   //      for (int i=0; i<WIDTHA; i++) begin
   //         oneD[(i+1)*WIDTHB-1 -: WIDTHB] = twoD[i];
   //      end
   //      return oneD;
   //   endfunction

   //    static function typ from_logic(logic[WIDTHA*WIDTHB-1:0] oneD);
   //       typ twoD;
   //       for (int i=0; i<WIDTHA; i++) begin
   //          twoD[i] = oneD[(i+1)*WIDTHB-1 -: WIDTHB];
   //       end
   //       return twoD;
   //    endfunction
      
   // endclass
   
endpackage
