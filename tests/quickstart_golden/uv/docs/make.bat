@ECHO OFF
setlocal

pushd %~dp0

REM Command file for Sphinx documentation
REM Written by scmd quickstart (sphinxcontrib-matlabdomain).
REM The commands run in the project's uv environment, as locked in uv.lock.

if "%UV%" == "" (
	set UV=uv run --frozen --group docs
)
if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=%UV% sphinx-build
)
if "%APIDOC%" == "" (
	set APIDOC=%UV% scmd apidoc
)
if "%SPHINXAUTOBUILD%" == "" (
	set SPHINXAUTOBUILD=%UV% sphinx-autobuild
)
set SOURCEDIR=.
set BUILDDIR=_build
REM The port of make livehtml; the build gives it to Simulink Help links.
if "%LIVEPORT%" == "" (
	set LIVEPORT=8000
)

uv --version >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'uv' command was not found: https://docs.astral.sh/uv/
	echo.
	popd
	exit /b 1
)

if "%1" == "" goto help

if "%1" == "apidoc" (
	%APIDOC% --conf-dir %SOURCEDIR%
	goto end
)

if "%1" == "apidoc-check" (
	%APIDOC% --conf-dir %SOURCEDIR% --check
	goto end
)

if "%1" == "livehtml" (
	%SPHINXAUTOBUILD% %SOURCEDIR% %BUILDDIR%/html -d %BUILDDIR%/doctrees --watch ".." --ignore "*/.venv/*" --ignore "*/.git/*" --pre-build "%APIDOC% --conf-dir . --quiet" --port %LIVEPORT% -D matlab_simulink_autobuild_server=http://127.0.0.1:%LIVEPORT%/ %SPHINXOPTS% %O%
	goto end
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
