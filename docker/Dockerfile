#   Dockerfile for gpsanapy with the 'recursive-directory' option
#   executes all gpx files in /csv_results shared directory
#   and returns the csv results in the same shared directory
#   BUILD & RUN with :
# 	sudo docker build -t gpsanapy .
# 	docker run -it --rm -v /home/gpx_files_and_results:/gpsanapy/csv_results gpsanapy

FROM python:3.7
RUN pip3 install --upgrade pip
RUN git clone https://github.com/jeanluc-auge/gpsanapy.git
RUN pip3 install -r /gpsanapy/requirements.txt
RUN mkdir /gpsanapy/csv_results
WORKDIR /gpsanapy/
CMD python3 src/core/gps_analysis.py -rd csv_results