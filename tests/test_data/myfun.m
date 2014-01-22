function [o1, o2, o3] = myfun(a1, a2)
% a fun function
%
% :param a1: the first input
% :param a2: another input
% :returns: ``[o1, o2, o3]`` some outputs

if nargin<1
  a1 = 0;
end
if nargin<2
  a2 = a1;
end
o1 = a1; o2 = a2; o3 = a1 + a2;
for n = 1:3
    o1 = o2;
    o2 = o3;
    o3 = o1 + o2;
end
