classdef Widget < handle
    %WIDGET A documented class.
    properties
        Value % the value
    end
    methods
        function obj = Widget(value)
            %WIDGET Make a widget; its output (the object) needs no section.
            %
            % Inputs:
            %   value - the initial value
            obj.Value = value;
        end
        function documented(obj, x)
            %DOCUMENTED A public method; the object needs no help.
            %
            % Inputs:
            %   x - the data
        end
        function undocumented(obj)
        end
        function r = noOutputs(obj)
            %NOOUTPUTS Returns a value but has no outputs section.
            r = obj.Value;
        end
        function skipMe(obj)
        end
        function set.Value(obj, v)
            obj.Value = v;
        end
    end
    methods (Static)
        function s = make(n)
            %MAKE A static method: its first input counts.
            s = n;
        end
    end
    methods (Access = private)
        function hiddenAway(obj)
        end
    end
    methods (Access = 'protected')
        function guarded(obj)
        end
    end
    methods (Hidden)
        function alsoHidden(obj)
        end
    end
    methods (Access = ?pkg.Other)
        function friend(obj)
        end
    end
    methods (Access = public)
        function explicit(obj)
            %EXPLICIT Access = public is public.
        end
    end
end
