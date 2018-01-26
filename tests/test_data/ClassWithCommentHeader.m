% This is a Comment Header
% Copyright (C) <year>, by <full_name>
%
% Some descriptions ...
%
% This header and all further comments above the class
% will be ignored by the documentation system.
%
% Lisence (GPL, BSD, etc.)
%

  % a comment with space indentation ...

    % a comment with tab indentation ...

classdef ClassWithCommentHeader
    % A class with a comment header on the top.

    properties
        link_name = 'none';     % name of the reference link
        pos       = zeros(3,1); % Cartesian position of the link
        rotm      = eye(3,3);   % (3 x 3) rotation matrix
        idx       = 0;          % index of the reference link
    end

    methods
        function obj = ClassWithCommentHeader(link_name, pos, rotm)
            % Constructor.
            %
            % :param link_name: Name of the reference link.
            % :param pos:       Cartesian position of the link.
            % :param rotm:      (3 x 3) rotation matrix.
            obj.link_name = link_name;
            obj.pos       = pos;
            obj.rotm      = rotm;
        end

        function tform = getTransformation(obj)
            % A transformation method in :class:`ClassWithCommentHeader`.
            %
            % :returns: ``tform``, a (4 x 4) homogeneous transformation matrix.
            tform = eye(4,4);
            tform(1:3,1:3) = obj.rotm;
            tform(1:3,4)   = obj.pos;
        end

    end
end
