function [o1, o2, o3] = myfun(a1, a2)
%MYFUN a fun function
%   [O1, O2, O3] = MYFUN(A1, A2) returns O given A
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
