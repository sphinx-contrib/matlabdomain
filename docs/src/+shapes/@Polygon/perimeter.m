function p = perimeter(obj)
% PERIMETER Length of the boundary of the polygon.
%
%   Outputs:
%     p - The sum of the edge lengths
p = sum(hypot(diff([obj.X obj.X(1)]), diff([obj.Y obj.Y(1)])));
end
