classdef Shape
    % SHAPE A named shape with a size.
    %
    %   s = demo.Shape("square", 2) creates a shape.

    properties
        Name = ""  % Display name
        Size = 1   % Edge length
    end

    methods
        function obj = Shape(name, size)
            % SHAPE Create a shape.
            obj.Name = name;
            obj.Size = size;
        end
        a = area(obj)
        obj = scale(obj, factor)
    end
end
