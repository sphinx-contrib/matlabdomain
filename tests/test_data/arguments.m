classdef arguments < handle & matlab.mixin.Copyable
   %ARGUMENTS Aggregate arguments for later

   properties (SetAccess=private, GetAccess=public)
      value
   end

   methods
      function obj = arguments()
         % Constructor for arguments
         obj.value = {};
      end
      function add(obj, foo)
         % Add new argument
         if isa(foo, 'arguments')
            for i = 1:length(foo.value)
               obj.value{end+1} = foo.value{i};
            end
         else
            obj.value{end+1} = foo;
         end
      end

   end

end
