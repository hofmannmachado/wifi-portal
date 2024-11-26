from flask import Flask, request, render_template_string
import subprocess
import glob

app = Flask(__name__)

wifi_client_device = "wlan1"
openvpn_dir = "/etc/openvpn/client/"
wireguard_dir = "/etc/wireguard/"

def get_current_wifi(interface="wlan1"):
    result = subprocess.check_output(["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list", "ifname", interface])
    for line in result.decode().split('\n'):
        if line.startswith("yes"):
            return line.split(":")[1]
    return "Not connected"

def get_connected_clients():
    result = subprocess.check_output(["arp", "-a"])
    return result.decode()

def control_wireguard(interface, action):
    result = subprocess.run(["wg-quick", action, interface], capture_output=True, text=True)
    if result.returncode == 0:
        return_str = f"Success to {action} WireGuard on {interface}: <pre>{result.stdout}</pre>"
    else:
        return_str = f"Failed to {action} WireGuard on {interface}: <pre>{result.stderr}</pre>"

    return_str += "<form action='/'><input type='submit' value='back' class='btn btn-primary'></form>"
    return return_str

def get_wireguard_interfaces():
    conf_files = glob.glob(f"{wireguard_dir}*.conf")
    interfaces = [f.split('/')[-1].split('.')[0] for f in conf_files]
    return interfaces

def get_wireguard_status(interface):
    result = subprocess.run(["wg", "show", interface], capture_output=True, text=True)
    if result.returncode == 0:
        return "Connected"
    else:
        return "Disconnected"

def get_wifi_clients():
    result = subprocess.check_output(["hostapd_cli", "all_sta"], text=True)
    clients = []
    for line in result.split("\n"):
        if "Station" in line:
            clients.append(line.split()[1])
    return clients

def get_openvpn_clients():
    conf_files = glob.glob(f"{openvpn_dir}*.ovpn")
    clients = [f.split('/')[-1].split('.')[0] for f in conf_files]
    return clients

def get_openvpn_status(client):
    result = subprocess.run(["pgrep", "-f", f"{openvpn_dir}{client}"], capture_output=True, text=True)
    if result.returncode == 0:
        return "Connected"
    else:
        return "Disconnected"

@app.route('/')
def index():
    result = subprocess.check_output(["nmcli", "--colors", "no", "-m", "multiline", "--get-value", "SSID", "dev", "wifi", "list", "ifname", wifi_client_device])
    ssids_list = result.decode().split('\n')
    interfaces = get_wireguard_interfaces()
    current_wifi = get_current_wifi()
    statuses = {iface: get_wireguard_status(iface) for iface in interfaces}
    openvpn_clients = get_openvpn_clients()
    openvpn_statuses = {client: get_openvpn_status(client) for client in openvpn_clients}
    
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Wifi Control</title>
        <!-- Bootstrap CSS CDN -->
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>Wifi Control</h1>
            <h2>Current Wifi: <span class="text-primary">{{ current_wifi }} ({{ wifi_client_device }})</span></h2>
            
            <h3>Connect to Wifi:</h3>
            <form action="/submit" method="post" class="form-inline">
                <select name="ssid" id="ssid" class="form-control mb-2 mr-sm-2">
                    {% for ssid in ssids_list %}
                        {% if ssid %}
                            <option value="{{ ssid }}">{{ ssid }}</option>
                        {% endif %}
                    {% endfor %}
                </select>
                <label for="password" class="mr-sm-2">Password:</label>
                <input type="password" name="password" class="form-control mb-2 mr-sm-2" />
                <input type="submit" value="Connect" class="btn btn-primary mb-2">
            </form>
            
            <h3>WireGuard Control</h3>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Interface</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for iface in interfaces %}
                    <tr>
                        <td>{{ iface }}</td>
                        <td>{{ statuses[iface] }}</td>
                        <td>
                            {% if statuses[iface] == "Connected" %}
                                <form action="/wireguard" method="post" class="d-inline">
                                    <input type="hidden" name="interface" value="{{ iface }}">
                                    <input type="hidden" name="action" value="down">
                                    <input type="submit" value="Disconnect" class="btn btn-danger">
                                </form>
                            {% else %}
                                <form action="/wireguard" method="post" class="d-inline">
                                    <input type="hidden" name="interface" value="{{ iface }}">
                                    <input type="hidden" name="action" value="up">
                                    <input type="submit" value="Connect" class="btn btn-success">
                                </form>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <h3>OpenVPN Control</h3>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Client</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for client in openvpn_clients %}
                    <tr>
                        <td>{{ client }}</td>
                        <td>{{ openvpn_statuses[client] }}</td>
                        <td>
                            {% if openvpn_statuses[client] == "Connected" %}
                                <form action="/openvpn" method="post" class="d-inline">
                                    <input type="hidden" name="client" value="{{ client }}">
                                    <input type="hidden" name="action" value="disconnect">
                                    <input type="submit" value="Disconnect" class="btn btn-danger">
                                </form>
                            {% else %}
                                <form action="/openvpn" method="post" class="d-inline">
                                    <input type="hidden" name="client" value="{{ client }}">
                                    <input type="hidden" name="action" value="connect">
                                    <input type="submit" value="Connect" class="btn btn-success">
                                </form>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Bootstrap JS and dependencies (optional, for interactive components) -->
        <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
    </body>
    </html>
    """
    
    return render_template_string(template, ssids_list=ssids_list, interfaces=interfaces, statuses=statuses, current_wifi=current_wifi, openvpn_clients=openvpn_clients, openvpn_statuses=openvpn_statuses, wifi_client_device=wifi_client_device)

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        ssid = request.form['ssid']
        password = request.form['password']
        connection_command = ["nmcli", "--colors", "no", "device", "wifi", "connect", ssid, "ifname", wifi_client_device]
        if len(password) > 0:
            connection_command.extend(["password", password])
        result = subprocess.run(connection_command, capture_output=True, text=True)
        if result.stderr:
            return f"Error: failed to connect to wifi network: <i>{result.stderr.decode()}</i>"
        elif result.stdout:
            return f"Success: <i>{result.stdout.decode()}</i>"
        return "Error: failed to connect."

@app.route('/current_wifi')
def current_wifi():
    current_wifi = get_current_wifi()
    return f"Current WiFi: {current_wifi}"

@app.route('/connected_clients')
def connected_clients():
    clients = get_connected_clients()
    return f"Connected Clients:<pre>{clients}</pre>"

@app.route('/wifi_clients')
def wifi_clients():
    clients = get_wifi_clients()
    return f"WiFi Clients:<pre>{clients}</pre>"

@app.route('/wireguard', methods=['POST'])
def wireguard():
    interface = request.form['interface']
    action = request.form['action']
    result = control_wireguard(interface, action)
    return result

@app.route('/openvpn', methods=['POST'])
def openvpn():
    client = request.form['client']
    action = request.form['action']
    result = control_openvpn(client, action)
    return result

if __name__ == '__main__':
    app.run(debug=True)
