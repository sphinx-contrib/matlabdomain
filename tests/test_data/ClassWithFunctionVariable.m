classdef ClassWithFunctionVariable
   % This line contains functions!

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

      function anotherMethodWithFunctions(obj, the_functions)
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

