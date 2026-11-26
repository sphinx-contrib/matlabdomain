function d = distance(p, q)
% DISTANCE Euclidean distance between two points.
%
%   d = demo.geometry.distance(p, q)
d = hypot(p.X - q.X, p.Y - q.Y);
end
