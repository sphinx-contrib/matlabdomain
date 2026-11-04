@ECHO OFF
setlocal

pushd %~dp0

REM Command file for Sphinx documentation
REM The commands run in the project's uv environment, as locked in uv.lock.

if "%UV%" == "" (
	set UV=uv run --frozen
)
if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=%UV% sphinx-build
)
if "%APIDOC%" == "" (
	set APIDOC=%UV% sphinx-matlab-apidoc
)
if "%SPHINXAUTOBUILD%" == "" (
	set SPHINXAUTOBUILD=%UV% sphinx-autobuild
)
set SOURCEDIR=.
set BUILDDIR=_build

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
	%APIDOC% -c %SOURCEDIR%
	goto end
)

if "%1" == "apidoc-check" (
	%APIDOC% -c %SOURCEDIR% --check
	goto end
)

if "%1" == "livehtml" (
	%SPHINXAUTOBUILD% %SOURCEDIR% %BUILDDIR%/html -d %BUILDDIR%/doctrees --watch .. --ignore "*/.venv/*" --ignore "*/.git/*" --pre-build "%APIDOC% -c . -q" %SPHINXOPTS% %O%
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
