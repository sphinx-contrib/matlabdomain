function total = totalArea(shapeList, opts)
% TOTALAREA Sum of the areas of several shapes.
%
%   total = shapes.totalArea(shapeList) adds the areas.
%   total = shapes.totalArea(shapeList, Scale=s) multiplies the sum by s.
%
%   The comments in the arguments blocks describe the inputs and the
%   output. matlab-api-check counts them; the documentation does not show
%   them, like MATLAB's help.
%
%   See also shapes.Circle
arguments
    shapeList (1,:) cell  % Shapes that have an area method
    opts.Scale (1,1) double = 1  % Factor applied to the sum
end
arguments (Output)
    total (1,1) double  % The scaled sum of the areas
end
total = opts.Scale * sum(cellfun(@(s) s.area(), shapeList));
checkPositive(total);
end
