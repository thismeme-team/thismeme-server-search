FROM nginx:latest
 
RUN rm /etc/nginx/conf.d/default.conf
COPY ./nginx-setup.conf /etc/nginx/conf.d/nginx-setup.conf

EXPOSE 80
 
CMD ["nginx", "-g", "daemon off;"]