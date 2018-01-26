% This is a Comment Header
% Copyright (C) <year>, by <full_name>
%
% Some descriptions ...
%
% This header and all further comments above the function
% will be ignored by the documentation system.
%
% Lisence (GPL, BSD, etc.)
%

  % a comment with space indentation ...

    % a comment with tab indentation ...

function [o1, o2, o3] = f_with_comment_header(a1, a2)
    % A simple function with a comment header on the top.

    % Check input args
    if (nargin < 1)
      a1 = 0;
    end
    if (nargin < 2)
      a2 = a1;
    end
    o1 = a1; o2 = a2; o3 = a1 + a2;

    for n = 1:3
        o1 = o2;
        o2 = o3;
        o3 = o1 + o2;
    end
end
