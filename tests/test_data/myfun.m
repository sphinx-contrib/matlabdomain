function o = myfun(a)
%MYFUN a fun function
%   O = MYFUN(A) returns O given A
if nargin<1
  o = 0;
elseif isstr(a)
  o = a
end