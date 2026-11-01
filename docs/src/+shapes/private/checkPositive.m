function checkPositive(value)
% CHECKPOSITIVE Error unless VALUE is positive (a private helper).
%
%   Inputs:
%     value - The number to check
if value <= 0
    error("shapes:notPositive", "The value must be positive.");
end
end
