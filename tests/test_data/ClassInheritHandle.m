classdef ClassInheritHandle < handle & my.super.Class
    % a handle class
    %
    % :param x: a variable

    %% some comments
    properties
        x % a property
    end
    methods
        function h = ClassInheritHandle(x)
            h.x = x
        end
        function x = get.x(obj)
        % Returns property x
            x = obj.x
        end
    end
    methods (Static)
        function w = a_static_function(z)
        % A static function in :class:`ClassInheritHandle`.
        %
        % :param z: input z
        % :returns: w

            w = z
        end
    end    
end
