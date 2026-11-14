classdef Circle < shapes.Shape
    % CIRCLE A circle with a radius.
    %
    %   c = shapes.Circle(2) creates a circle of radius 2.
    %
    %   See also shapes.Shape, shapes.totalArea

    properties
        Radius (1,1) double {mustBePositive} = 1  % Radius, in meters
    end

    properties (Hidden)
        Tag = ""  % Free text, hidden from the documentation by default
    end

    methods
        function obj = Circle(radius)
            % CIRCLE Create a circle.
            %
            %   Inputs:
            %     radius - The radius, a positive number
            arguments
                radius (1,1) double {mustBePositive}
            end
            obj.Name = "circle";
            obj.Radius = radius;
        end

        function a = area(obj)
            % AREA Area of the circle.
            %
            %   Outputs:
            %     a - pi times the radius squared
            a = pi * obj.Radius^2;
        end
    end

    methods (Static)
        function c = unit()
            % UNIT A circle of radius 1.
            %
            %   Outputs:
            %     c - The circle
            c = shapes.Circle(1);
        end
    end

    methods (Access = private)
        function check(obj)
            % CHECK Internal consistency check.
            assert(obj.Radius > 0);
        end
    end
end
