import libvirt
import xml.etree.ElementTree as ET

def get_mac_address(domain):

    try:
        # Connect to the libvirt daemon
        conn = libvirt.open()
        if conn is None:
            raise RuntimeError("Failed to open connection to the hypervisor.")

        # Lookup the domain by name
        vm = conn.lookupByName(domain)
        if vm is None:
            raise ValueError(f"Domain '{domain}' not found.")

        # Get the XML description of the domain
        xml_desc = vm.XMLDesc()

        # Parse the XML to extract the MAC address
        root = ET.fromstring(xml_desc)
        mac_element = root.find(".//mac")
        if mac_element is not None:
            mac_address = mac_element.attrib.get('address')
            return mac_address
        else:
            raise ValueError("MAC address not found in XML.")

    except libvirt.libvirtError as e:
        return f"A libvirt error occurred: {e}"
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        if conn:
            conn.close()

# Replace 'debian' with your domain name
domain_name = "debian"
mac_address = get_mac_address(domain_name)
print(f"MAC Address: {mac_address}")
