classdef ClassWithUndocumentedMembers
   % A class where some members are not documented.
   
   methods
      function obj = ClassWithUndocumentedMembers()
         % Constructor
         disp('Constructed')

      end

      function documented(obj)
          % Has documentation         
          disp('documented')
      end

      function undocumented(obj)
         disp('undocumented')
      end
   end
end

