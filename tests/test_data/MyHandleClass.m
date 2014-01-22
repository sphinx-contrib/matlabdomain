classdef MyHandleClass < handle & my.super.Class
    % a handle class
    %
    % :param x: a variable

    %% some comments
    properties
        x % a property
    end

    methods
        function h = MyHandleClass(x)
            h.x = x
        end
    end

end
