classdef ClassWithFunctionVariable
   % A class with a method with a variable starting with function
   
   properties
      info;
   end
      
   methods
      function obj = ClassWithFunctionVariable(the_functions)       
         % Constructor
         
         % Determine the name and M-file location of the function handle.
         functionHandleInfo = functions(testFcn);
         self.Name = functionHandleInfo.function;
         if strcmp(functionHandleInfo.type, 'anonymous')
            % Anonymous function handles don't have an M-file location.
            self.Location = '';
         else
            self.Location = functionHandleInfo.file;
         end
      end

   end
end

