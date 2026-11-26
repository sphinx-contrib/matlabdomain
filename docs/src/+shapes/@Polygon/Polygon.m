classdef Polygon < shapes.Shape
    % POLYGON A polygon, defined in a class folder.
    %
    %   p = shapes.Polygon([0 1 0], [0 0 1]) creates a triangle. The method
    %   perimeter is defined in its own file, @Polygon/perimeter.m.

    properties
        X (1,:) double  % Horizontal coordinates of the corners
        Y (1,:) double  % Vertical coordinates of the corners
    end

    methods
        function obj = Polygon(x, y)
            % POLYGON Create a polygon from its corners.
            %
            %   Inputs:
            %
            %   * x - Horizontal coordinates
            %   * y - Vertical coordinates
            obj.Name = "polygon";
            obj.X = x;
            obj.Y = y;
        end

        function a = area(obj)
            % AREA Area enclosed by the polygon.
            %
            %   Outputs:
            %     a - The area (shoelace formula)
            a = abs(sum(obj.X .* circshift(obj.Y, -1) - circshift(obj.X, -1) .* obj.Y)) / 2;
        end

        p = perimeter(obj)
    end
end
