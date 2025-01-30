#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <assert.h>
#ifdef _WIN32
#include <Winsock2.h>
#include <windows.h>
#else
#include <unistd.h>
#endif
#include <errno.h>
#include <xscope_endpoint.h>

#define CMD_DEVICE_SHUTDOWN (1)

#define LINE_LENGTH 1024

#define XSCOPE_ID_CONNECT (0)
#define XSCOPE_ID_COMMAND_RETURN (1)

int connected = 0;

#define RET_NO_RESULT (255)
unsigned char ret = RET_NO_RESULT;

static char get_next_char(const char **buffer)
{
    const char *ptr = *buffer;
    while (*ptr && isspace(*ptr)) {
        ptr++;
    }

    *buffer = ptr + 1;
    return *ptr;
}

static int convert_atoi_substr(const char **buffer)
{
    const char *ptr = *buffer;
    unsigned int value = 0;
    while (*ptr && isspace(*ptr)) {
        ptr++;
    }

    if (*ptr == '\0') {
        return 0;
    }

    value = atoi((char*)ptr);

    while (*ptr && !isspace(*ptr)) {
        ptr++;
    }

    *buffer = ptr;
    return value;
}

#define COMMAND_RESPONSE_POLL_MS (1)
#define COMMAND_RESPONSE_TIMEOUT_MS (3000)
#define COMMAND_RESPONSE_ITERS (COMMAND_RESPONSE_TIMEOUT_MS / COMMAND_RESPONSE_POLL_MS)
unsigned char wait_for_command_response()
{
    for (int i = 0; i < COMMAND_RESPONSE_ITERS; ++i) {
#ifdef _WIN32
        Sleep(COMMAND_RESPONSE_POLL_MS);
#else
        usleep(COMMAND_RESPONSE_POLL_MS * 1000);
#endif

        if (ret != RET_NO_RESULT) {
            if (ret != 0)
                fprintf(stderr, "Command failed, error code %u\n", ret);
            return ret;
        }
    }

    fprintf(stderr, "Timed out waiting for command response\n");
    return RET_NO_RESULT;
}

void xscope_print(unsigned long long timestamp,
                  unsigned int length,
                  unsigned char *data) {
    if (length) {
        for (unsigned i = 0; i < length; i++) {
            fprintf(stderr, "%c", *(&data[i]));
            fflush(stderr);
        }
    }
}

void xscope_record(unsigned int id,
                   unsigned long long timestamp,
                   unsigned int length,
                   unsigned long long dataval,
                   unsigned char *databytes)
{
    switch(id) {
    case XSCOPE_ID_CONNECT:
        if (length != 1) {
            fprintf(stderr, "unexpected length %u in connection response\n", length);
            return;
        }
        connected = 1;
        return;

    case XSCOPE_ID_COMMAND_RETURN:
        if (length != 1) {
            fprintf(stderr, "unexpected length %u in command response\n", length);
            return;
        }
        ret = databytes[0];
        return;

   default:
       fprintf(stderr, "xscope_record: unexpected ID %u\n", id);
       return;
   }
}

#define CONNECT_POLL_MS (1)
#define CONNECT_TIMEOUT_MS (10000)
#define CONNECT_ITERS (CONNECT_TIMEOUT_MS / CONNECT_POLL_MS)

int main(int argc, char *argv[]) {
    /* Having run with the xscope-port argument all prints from the xCORE
     * will be directed to the socket, so they need to be printed from here
     */
    xscope_ep_set_print_cb(xscope_print);

    xscope_ep_set_record_cb(xscope_record);

    printf("command = %s\n", argv[3]);

    if (argc > 3) {
        /* argv[1] = ip address
         * argv[2] = port number
         * argv[3] = command
         */
        xscope_ep_connect(argv[1], argv[2]);

        if(strcmp(argv[3], "connect") == 0)
        {
            printf("Wait for device to connect...\n");
            int iters = 0;
            while(1) {
    #ifdef _WIN32
                Sleep(CONNECT_POLL_MS);
    #else
                usleep(CONNECT_POLL_MS * 1000);
    #endif

                if (connected)
                    break;

                ++iters;
                if (iters == CONNECT_ITERS) {
                    fprintf(stderr, "Timed out waiting for xSCOPE connection handshake\n");
                    return 1;
                }
            }
        } // if(strcmp(argv[3], "connect") == 0)
        else if(strcmp(argv[3], "shutdown") == 0)
        {
            printf("Send shutdown cmd to device\n");
            char to_send[1];
            to_send[0] = CMD_DEVICE_SHUTDOWN;
            fprintf(stderr, "Sending %d\n", to_send[0]);
            while (xscope_ep_request_upload(1, (unsigned char *)&to_send) != XSCOPE_EP_SUCCESS);
            unsigned char result = wait_for_command_response();
            printf("shutdown response received %d\n", ret);
            if (result != 0)
            {
                return 1;
            }
        }
    } else {
        fprintf(stderr, "Usage: host_address port [commands to send via xscope...]\n");
        return 1;
    }

    fprintf(stderr, "Shutting down...\n");
    fflush(stderr);
    xscope_ep_disconnect();

    return 0;
}
