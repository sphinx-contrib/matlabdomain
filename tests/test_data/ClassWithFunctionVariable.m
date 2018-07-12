classdef ClassWithFunctionVariable
   % A class with a method with a variable starting with function
   
   properties
      info;
   end
      
   methods
      function obj = ClassWithFunctionVariable(the_functions)       
         % Constructor
         
         % Pygment 2.2 does not parse variables starting with function*
         % correctly. 
         functionHandleInfo = functions(the_functions);
         obj.info = functionHandleInfo;
      end

   end
end

