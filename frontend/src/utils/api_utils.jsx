import axios from 'axios';

const baseURL = "http://localhost:8000";

const request_handler = axios.create({
  baseURL: baseURL,
  timeout: 15000,
});

function request({ 
  method = 'GET', 
  url = '', 
  data = null, 
  params = null, 
  headers = {}, 
  onSuccess, 
  onError 
}) {

  const fullUrl = new URL(url, baseURL);
  if (params) {
    Object.keys(params).forEach(key => fullUrl.searchParams.append(key, params[key]));
  }

  request_handler({
    method,
    url,
    data,
    params,
    headers,
  })
    .then(async (response) => {
      if (onSuccess && typeof onSuccess === 'function') {
        await onSuccess(response.data);
      }
    })
    .catch(async (error) => {
      if (onError && typeof onError === 'function') {
        if (error.response) {
          await onError({
            status: error.response.status,
            data: error.response.data,
            message: error.message,
          });
        } else if (error.request) {
          await onError({ message: 'No response from server', request: error.request });
        } else {
          await onError({ message: error.message });
        }
      } 
    });
}

export default request;
