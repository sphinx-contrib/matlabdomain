classdef Shape < handle
    % SHAPE Base class of the shapes in this namespace.
    %
    %   Every shape has a name and a fill color, and can describe itself.
    %
    %   Shape Properties:
    %     Name - Display name
    %     Color - Fill color
    %
    %   Shape Methods:
    %     describe - One line about the shape
    %
    %   See also shapes.Circle, shapes.Color

    properties
        Name (1,1) string = "shape"  % Display name
    end

    properties (SetAccess = protected)
        Color (1,1) shapes.Color = shapes.Color.Red  % Fill color
    end

    methods
        function text = describe(obj)
            % DESCRIBE One line about the shape, such as "circle (Red)".
            text = sprintf("%s (%s)", obj.Name, string(obj.Color));
        end
    end
end
