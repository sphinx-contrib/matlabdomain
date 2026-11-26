function check_range(lo, hi)
% CHECK_RANGE Error unless LO <= HI (private to utils/).
assert(lo <= hi, "lo must not exceed hi");
end
