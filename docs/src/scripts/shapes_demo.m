% SHAPES_DEMO Create two shapes and print their total area.
%
%   Run it from the folder that contains +shapes.

c = shapes.Circle(2);
p = shapes.Polygon([0 1 0], [0 0 1]);
fprintf("Total area: %g\n", shapes.totalArea({c, p}));
